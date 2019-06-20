############################################################################# 
## eegBidsCreator is a package converting EEG/MEG from Embla format
## to EDF(+), Brain Vision or MEEG (SPM12) format. 
## The converted samples are structured following BIDS 1.2.0 standard 
## https://bids-specification.readthedocs.io/en/stable/
############################################################################# 
## Copyright (c) 2018-2019, University of Liège
## Author: Nikita Beliy
## Owner: Liege University https://www.uliege.be
## Version: 0.74
## Maintainer: Nikita Beliy
## Email: Nikita.Beliy@uliege.be
## Status: developpement
############################################################################# 
## This file is part of eegBidsCreator                                     
## eegBidsCreator is free software: you can redistribute it and/or modify     
## it under the terms of the GNU General Public License as published by     
## the Free Software Foundation, either version 2 of the License, or     
## (at your option) any later version.      
## eegBidsCreator is distributed in the hope that it will be useful,     
## but WITHOUT ANY WARRANTY; without even the implied warranty of     
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the     
## GNU General Public License for more details.      
## You should have received a copy of the GNU General Public License     
## along with eegBidsCreator.  If not, see <https://www.gnu.org/licenses/>.
############################################################################


import logging
import os
import glob
import traceback
import tempfile
import warnings
from datetime import datetime, timedelta
import time as tm
import importlib.util
import shutil
import psutil

import tools.cfi as cfi
import tools.cli as cli
import tools.tools as tools

# Generic classes import
import DataStructure.Generic.Record as GenericRecord
import DataStructure.Generic.Event as GenericEvent
import DataStructure.Generic.Channel as GenericChannel

# Format implementation import
from DataStructure.SPM12.MEEG import MEEG

from DataStructure.Embla.Record import EmbRecord

from DataStructure.BrainVision.BrainVision import BrainVision
from DataStructure.BrainVision.Channel import BvChannel

from DataStructure.EDF.EDF import EDF
from DataStructure.EDF.EDF import Channel as EDFChannel


VERSION = 'dev0.75'


def main(argv):

    process = psutil.Process(os.getpid())
    recording = None
    outData = None

    argv_plugin = []
    if '--' in argv:
        argv_plugin = argv[argv.index('--') + 1:]
        argv = argv[:argv.index('--')]

    ex_code = 0
    args = cli.parce_CLI(argv[1:], VERSION)

    parameters = cfi.default_parameters()
    if args.config_file:
        cfi.read_parameters(parameters, args.config_file[0])

    # Overloading values by command-line arguments
    if args.sub is not None: 
        parameters['GENERAL']['PatientId'] = args.sub
    if args.ses is not None: 
        parameters['GENERAL']['SessionId'] = args.ses
    if args.task is not None:
        parameters['GENERAL']['TaskId'] = args.task
    if args.acq is not None:
        parameters['GENERAL']['AcquisitionId'] = args.acq
    if args.run is not None:
        parameters['GENERAL']['RunId'] = args.run
    if args.eegJson is not None:
        parameters['GENERAL']['JsonFile'] = args.eegJson
    if args.conv is not None:
        parameters['GENERAL']['Conversion'] = args.conv
    if args.infile is not None:
        parameters['GENERAL']['Path'] = os.path.realpath(args.infile[0])
    if args.outdir is not None:
        parameters['GENERAL']['OutputFolder'] = \
                os.path.realpath(args.outdir[0])
    if args.mem is not None:
        parameters['GENERAL']['MemoryUsage'] = str(args.mem[0])
    if args.loglevel is not None:
        parameters['LOGGING']['LogLevel'] = args.loglevel
    if args.logfile is not None:
        parameters['LOGGING']['LogFile'] = args.logfile[0]
    if args.quiet is True:
        parameters['LOGGING']['Quiet'] = 'yes'

    if parameters['GENERAL']['OutputFolder'][-1] != '/':
        parameters['GENERAL']['OutputFolder'] += '/'
    if parameters['GENERAL']['Path'][-1] != '/':
        parameters['GENERAL']['Path'] += '/'

    if not cfi.check_configuration(parameters):
        raise Exception("Errors in configuration file")

    # Setup logging.
    # Logfile will be stored into temporary directory first,
    # then moved to output directory.
    try:
        tmpDir = tempfile.mkdtemp(
                prefix=os.path.basename(argv[0]) + "_") + "/"
    except FileNotFoundError:
        warnings.warn("TMPDIR: Failed to create temporary directory."
                      "Will try current directory")
        tmpDir = tempfile.mkdtemp(
                prefix=os.path.basename(argv[0]) + "_",dir=".") + "/"

    # Alternate formatter:
    # logFormatter = logging.Formatter(
    #    "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
    #    datefmt='%m/%d/%Y %H:%M:%S')
    logFormatter = logging.Formatter(
            "[%(levelname)-7.7s]:%(asctime)s:%(name)s %(message)s",
            datefmt='%m/%d/%Y %H:%M:%S')
    Logger = logging.getLogger()

    fileHandler = logging.FileHandler(tmpDir + "logfile", mode='w')
    fileHandler.setFormatter(logFormatter)
    Logger.addHandler(fileHandler)

    Logger.setLevel(getattr(logging, parameters['LOGGING']['LogLevel'], None))
    if parameters['LOGGING']['LogFile'] != "":
        fileHandler2 = logging.FileHandler(
                parameters['LOGGING']['LogFile'], mode='w')
        fileHandler2.setFormatter(logFormatter)
        Logger.addHandler(fileHandler2)

    if not parameters['LOGGING'].getboolean('Quiet'):
        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(logFormatter)
        Logger.addHandler(consoleHandler)

    SetupBIDS()

    ANONYM_DATE = None
    ANONYM_NAME = None
    ANONYM_BIRTH = None
    if parameters.getboolean("ANONYMIZATION","Anonymize"):
        if parameters["ANONYMIZATION"]["StartDate"] != "None" and \
                parameters["ANONYMIZATION"]["StartDate"] != "":
            ANONYM_DATE = datetime.strptime(
                    parameters["ANONYMIZATION"]["StartDate"],"%Y-%m-%d")
        if parameters["ANONYMIZATION"]["SubjName"] != "None":
            ANONYM_NAME = parameters["ANONYMIZATION"]["SubjName"]
        if parameters["ANONYMIZATION"]["BirthDate"] != "None":
            if parameters["ANONYMIZATION"]["BirthDate"] == "" :
                ANONYM_BIRTH = ""
            else:
                ANONYM_BIRTH = datetime.strptime(
                        parameters["ANONYMIZATION"]["BirthDate"],"%Y-%m-%d")

    entry_points = \
        ["RecordingEP", "ChannelsEP", "EventsEP", "RunsEP", "DataEP"]
    plugins = dict()
    pl_name = ""
    if parameters["PLUGINS"]["Plugin"] != "":
        if not os.path.exists(parameters["PLUGINS"]["Plugin"]):
            raise FileNotFoundError(
                    "Plug-in file {} not found".format(
                        parameters["PLUGINS"]["Plugin"]))
        pl_name = os.path.splitext(
                os.path.basename(parameters["PLUGINS"]["Plugin"]))[0]
        Logger.info(
                "Loading module {} from {}".format(
                    pl_name, parameters["PLUGINS"]["Plugin"]))
        spec = importlib.util.spec_from_file_location(
                pl_name, parameters["PLUGINS"]["Plugin"])
        if spec is None:
            raise Exception(
                    "Unable to load module {} from {}".format(
                        pl_name, parameters["PLUGINS"]["Plugin"]))
        itertools = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(itertools)
        f_list = dir(itertools)
        for ep in entry_points:
            if ep in f_list and callable(getattr(itertools,ep)):
                Logger.debug("Entry point {} found".format(ep))
                plugins[ep] = getattr(itertools,ep)
        if len(plugins) == 0:
            Logger.warning(
                    "Plugin {} loaded but "
                    "no compatible functions found".format(pl_name))

    Logger.info(">>>>>>>>>>>>>>>>>>>>>>")
    Logger.info("Starting new bidsifier")
    Logger.info("<<<<<<<<<<<<<<<<<<<<<<")

    Logger.debug(str(os.sys.argv))
    Logger.debug("Process PID: " + str(os.getpid()))
    Logger.debug("Temporary directory: " + tmpDir)
    with open(tmpDir + "configuration", 
              'w', encoding='utf-8') as configfile: 
        parameters.write(configfile)

    Logger.info("File: {}".format(parameters['GENERAL']['Path']))
    basename = os.path.basename(parameters['GENERAL']['Path'][0:-1])
    recording = None
    try:
        if EmbRecord.IsValidInput(parameters['GENERAL']['Path']):
                recording = EmbRecord()
        else:
            raise Exception("Unable determine eeg format")

        recording.SetOutputPath(parameters['GENERAL']['OutputFolder'])
        recording.SetInputPath(parameters['GENERAL']['Path'])

        recording.SetId(session=parameters['GENERAL']["SessionId"], 
                        task=parameters['GENERAL']["TaskId"],
                        acquisition=parameters['GENERAL']["AcquisitionId"])
        if parameters['GENERAL']["RunId"] != "":
            recording.SetRun(int(parameters['GENERAL']["RunId"]))

        recording.LoadMetadata()
        if parameters['GENERAL']["PatientId"] != "":
            recording.SetId(subject=parameters['GENERAL']["PatientId"])
            recording.SubjectInfo.ID = parameters['GENERAL']["PatientId"]

        if entry_points[0] in plugins:
            try:
                result = 0
                result = plugins[entry_points[0]](
                        recording, 
                        argv_plugin,
                        parameters["PLUGINS"])
                if result != 0:
                    raise Exception("Plugin {} returned code {}"
                                    .format(entry_points[0], result))
            except Exception:
                ex_code = 100 + 0 + result
                raise

        if parameters['GENERAL']['JsonFile'] != "":
            recording.LoadJson(parameters['GENERAL']['JsonFile'])

        Logger.info("Patient Id: {}".format(recording.SubjectInfo.ID))
        Logger.info("Session Id: " + recording.GetSession())
        Logger.info("Task    Id: " + recording.GetTask())
        Logger.info("Acq     Id: " + recording.GetAcquisition())
        if recording.GetRun() is not None:
            Logger.info("Run     Id: " + str(recording.GetRun()))

        recording.Lock()

        ###########################
        # Creating output folders #
        ###########################

        try:
            tools.create_directory(
                    path=recording.Path(appdir="eeg"),
                    toRemove=recording.GetPrefix(app="*"),
                    allowDups=parameters["GENERAL"]
                    .getboolean("OverideDuplicated"))

            tools.create_directory(
                    path=parameters['GENERAL']['OutputFolder'] 
                    + "sourcedata/log",
                    toRemove=recording.GetPrefix(app=".log"),
                    allowDups=True)

            tools.create_directory(
                    path=parameters['GENERAL']['OutputFolder'] 
                    + "sourcedata/configuration",
                    toRemove=recording.GetPrefix(app=".ini"),
                    allowDups=True)

            if parameters['GENERAL'].getboolean('CopySource'):
                srcPath = parameters['GENERAL']['OutputFolder']\
                          + "sourcedata/"
                tools.create_directory(
                        path=srcPath,
                        toRemove=basename,
                        allowDups=parameters["GENERAL"]
                        .getboolean("OverideDuplicated"))
                Logger.info("Copiyng original data to sourcedata folder")
                shutil.copytree(recording.GetInputPath(),
                                srcPath + basename)
        except FileExistsError as e:
            ex_code = 10
            raise

        if not recording.GetStartTime():
            Logger.warning("Unable to get StartTime of record. "
                           "Will be set to first data point.")
        if not recording.GetStopTime():
            Logger.warning("Unable to get EndTime of record. "
                           "Will be set to last data point.")

        ####################
        # Reading channels #
        ####################

        Logger.info("Reading channels")
        main_channel = None
        to_keep = []
        if parameters["CHANNELS"]["WhiteList"] != "":
            to_keep = [p.strip() for p in
                       parameters['CHANNELS']['WhiteList'].split(',')]
        to_drop = []
        if parameters["CHANNELS"]["BlackList"] != "":
            to_drop = [p.strip() for p in
                       parameters['CHANNELS']['BlackList'].split(',')]

        recording.ReadChannels(white_list=to_keep,
                               black_list=to_drop,
                               bidsify=not parameters["BIDS"]
                               .getboolean("OriginalTypes"))
        recording.SetMainChannel(parameters["CHANNELS"]["MainChannel"])

        if recording.GetStartTime() and recording.GetStopTime():
            ddt = recording.GetMaxTime() - recording.GetMinTime()
            ddt -= recording.GetStopTime() - recording.GetStartTime()
            if abs(ddt.total_seconds()) > 3600:
                Logger.warning(
                        "Record duration is shorter by {} than data taking. "
                        "Updating Start and Stop times".format(ddt))
                recording.SetStartTime(recording.GetMinTime(),
                                       recording.GetMaxTime())
        t_ref, t_end = recording.SetReferenceTime()

        if entry_points[1] in plugins:
            try:
                result = 0
                result = plugins[entry_points[1]](
                        recording, 
                        argv_plugin, 
                        parameters["PLUGINS"])
                if result != 0:
                    raise Exception("Plugin {} returned code {}"
                                    .format(entry_points[1], result))
            except Exception:
                ex_code = 100 + 10 + result
                raise

        if not t_ref or not t_end:
            raise ValueError("Unable to determine reference times")

        Logger.debug("Start time: {}, Stop time: {}".format(
            recording.GetStartTime(True), recording.GetStopTime(True)))
        Logger.debug("Earliest time: {}, Latest time: {}".format(
            recording.GetMinTime(True), recording.GetMaxTime(True)))
        Logger.debug("Ref start time: {}, ref end time: {}".format(
            recording.GetRefTime(True), recording.GetEndTime(True)))
        Logger.info("Duration: {}".format(t_end - t_ref))

        t_l = None
        t_h = None
        if parameters['DATATREATMENT']['StartTime'] != '':
            t_l = datetime.strptime(parameters['DATATREATMENT']['StartTime'],
                                    "%Y-%m-%d %H:%M:%S")
        if parameters['DATATREATMENT']['EndTime'] != '':
            t_h = datetime.strptime(parameters['DATATREATMENT']['StartTime'],
                                    "%Y-%m-%d %H:%M:%S")
        t_ref, t_end = recording.CropTime(t_l, t_h, verbose=True)

        ####################
        # Reading events   #
        ####################

        Logger.info("Reading events info")
        to_keep = []
        if parameters['EVENTS']['WhiteList'] != '':
            to_keep = [p.strip() 
                       for p in parameters['EVENTS']['WhiteList'].split(',')]
        to_drop = []
        if parameters['EVENTS']['BlackList'] != '':
            to_drop = [p.strip() 
                       for p in parameters['EVENTS']['BlackList'].split(',')]

        recording.ReadEvents(to_keep, to_drop)
        t_ev_min = None
        if parameters["DATATREATMENT"]["StartEvent"] != "":
            pos = recording.SearchEvent(
                    parameters["DATATREATMENT"]["StartEvent"],
                    MinTime=t_ref)
            if pos is not None:
                t_ev_min = recording.Events[pos].GetTime()

        t_ev_max = None
        if parameters["DATATREATMENT"]["EndEvent"] != "":
            pos = recording.RSearchEvent(
                    parameters["DATATREATMENT"]["EndEvent"],
                    MinTime=t_ref)
            if pos is not None:
                t_ev_max = recording.Events[pos].GetTime()
        t_ref, t_end = recording.CropTime(t_ev_min, t_ev_max, verbose=True)

        if parameters.getboolean("EVENTS","IncludeSegmentStart"):
            if recording.GetMainChannel():
                main_channel = recording.GetMainChannel()
                for t in range(0, main_channel.GetNsequences()):
                    ev = GenericEvent.GenEvent(
                                  Name="New Segment", 
                                  Time=main_channel.GetSequenceStart(t), 
                                  Duration=main_channel.GetSequenceDuration(t))
                    ev.AddChannel(main_channel.GetId())
                    recording.AddEvents(ev)
            else:
                Logger.warning(
                        "Main Channel is not defined."
                        "Switching off IncludeSegmentStart")
                parameters["EVENTS"]["IncludeSegmentStart"] = "no"

        if entry_points[2] in plugins:
            try:
                result = 0
                result = plugins[entry_points[2]](
                        recording,
                        argv_plugin,
                        parameters["PLUGINS"])
                if result != 0:
                    raise Exception(
                            "Plugin {} returned code {}"
                            .format(entry_points[2], result))
            except Exception:
                ex_code = 100 + 20 + result
                raise

        ################################
        # Creating meta-data json file #
        ################################

        recording.UpdateJSON()
        res = recording.CheckJSON()
        if len(res[0]) > 0:
            Logger.warning("JSON: Missing next required fields: "
                           + str(res[0]))
        if len(res[1]) > 0:
            Logger.info("JSON: Missing next recomennded fields: "
                        + str(res[1]))
        if len(res[2]) > 0:
            Logger.debug("JSON: Missing next optional fields: "
                         + str(res[2]))
        if len(res[3]) > 0:
            Logger.warning("JSON: Contains next non BIDS fields: "
                           + str(res[3]))

        ############################
        # Updating channels        #
        # frequency multiplier     #
        # and starting time        #
        ############################

        for c in recording.Channels:
            c.SetFrequencyMultiplyer(int(
                recording.Frequency / c.GetFrequency()))

        time_limits = None
        if recording.GetRun is not None \
                or parameters["RUNS"]["SplitRuns"] == "":
            time_limits = [[t_ref, t_end]]
        elif parameters["RUNS"]["SplitRuns"] == "Channel":
            time_limits = recording.GetRuns(
                    min_span=60 * float(parameters["RUNS"]["MinSpan"]))
        elif parameters["RUNS"]["SplitRuns"] == "EventSpan":
            opEvl = [opEv.strip() for opEv in 
                     parameters["RUNS"]["OpeningEvents"].split(',')]
            time_limits = recording.GetRuns(
                    openingEvents=opEvl,
                    min_span=60 * float(parameters["RUNS"]["MinSpan"]))
        elif parameters["RUNS"]["SplitRuns"] == "EventLimit":
            opEvl = [opEv.strip() for opEv in 
                     parameters["RUNS"]["OpeningEvents"].split(',')]
            clEvl = [clEv.strip() for clEv in 
                     parameters["RUNS"]["ClosingEvents"].split(',')]
            time_limits = recording.GetRuns(
                    openingEvents=opEvl, closingEvents=clEvl,
                    min_span=60 * float(parameters["RUNS"]["MinSpan"]))
        else: 
            raise ValueError("Unknown method for run spitting: {}"
                             .format(parameters["RUNS"]["SplitRuns"]))

        if len(time_limits) == 0:
            raise Exception("No valid runs found")

        if entry_points[3] in plugins:
            try:
                result = 0
                result = plugins[entry_points[3]](
                         recording,
                         time_limits,
                         argv_plugin,
                         parameters["PLUGINS"])
                if result != 0:
                    raise Exception(
                            "Plugin {} returned code {}"
                            .format(entry_points[3], result))
            except Exception:
                ex_code = 100 + 30 + result
                raise

        #####################
        # Running over runs #
        #####################

        file_list = list()
        mem_requested = float(parameters["GENERAL"]["MemoryUsage"])\
            * (1024 ** 3)
        if parameters['GENERAL']['Conversion'] == "EDF":
            mem_1s = 32 * sum(ch.GetFrequency() for ch in recording.Channels)
        elif parameters['GENERAL']['Conversion'] == "BV": 
            mem_1s = 32 * len(recording.Channels) * recording.Frequency
        elif parameters['GENERAL']['Conversion'] == "MEEG": 
            mem_1s = 32 * len(recording.Channels) * recording.Frequency

        for count,t in enumerate(time_limits):
            t_ref = t[0].replace(microsecond=0)
            t_end = t[1].replace(microsecond=0) + timedelta(seconds=1)

            # Getting list of channels and events
            channels = recording.Channels

            if parameters["EVENTS"].getboolean("IgnoreOutOfTimeEvents"):
                events = recording.EventsInTime(t_ref, t_end)
            else:
                events = recording.EventsInTime()

            # Updating channels reference time
            for c in recording.Channels:
                c.SetStartTime(t_ref)

            # Run definition
            if len(time_limits) > 1:
                Logger.info("Run {}: duration: {}".format(count + 1,
                                                          t_end - t_ref))
                recording.SetRun(count + 1)

            recording.DumpJSON()
            Logger.info("Creating channels.tsv file")
            with open(recording.Path(appdir="eeg",
                                     appfile=recording.GetPrefix()
                                     + "_channels.tsv"),
                      "w", 
                      encoding='utf-8') as f:
                GenericChannel.GenChannel.BIDSfields.DumpDefinitions(
                        recording.Path(appdir="eeg")
                        + recording.GetPrefix()
                        + "_channels.json"
                        )
                print(GenericChannel.GenChannel.BIDSfields.GetHeader(), file=f)
                for c in channels:
                    c.BIDSvalues["name"] = c.GetName()
                    c.BIDSvalues["type"] = c.GetType()
                    c.BIDSvalues["units"] = c.GetUnit()
                    c.BIDSvalues["description"] = c.GetDescription()
                    c.BIDSvalues["sampling_frequency"] = c.GetFrequency()
                    c.BIDSvalues["reference"] = c.GetReference()
                    print(c.BIDSfields.GetLine(c.BIDSvalues), file=f)

            Logger.info("Creating events.tsv file")     
            GenericEvent.GenEvent.BIDSfields.DumpDefinitions(
                    recording.Path(appdir="eeg")
                    + recording.GetPrefix(app="_events.json"))
            with open(recording.Path(appdir="eeg")
                      + recording.GetPrefix(app="_events.tsv"),
                      "w", encoding='utf-8') as f:
                print(GenericEvent.GenEvent.BIDSfields.GetHeader(), file=f)
                for ev in events:
                    ev.BIDSvalues["onset"] = ev.GetOffset(t_ref)
                    ev.BIDSvalues["duration"] = ev.GetDuration()
                    ev.BIDSvalues["trial_type"] = ev.GetName()
                    if ev.GetChannelsSize() == 0\
                       or parameters.getboolean("EVENTS","MergeCommonEvents"):
                        ev.BIDSvalues["channels"] = ev.GetChannels()
                        print(ev.BIDSfields.GetLine(ev.BIDSvalues), file=f)
                    else :
                        for c_id in ev.GetChannels():
                            ev.BIDSvalues["channels"] = ev.GetChannelById(c_id)
                            print(ev.BIDSfields.GetLine(ev.libValues), file=f)

            # BV format
            if parameters['GENERAL']['Conversion'] == "BV":
                Logger.info("Converting to BrainVision format")
                outData = BrainVision(recording.Path(appdir="eeg"),
                                      recording.GetPrefix(),
                                      AnonymDate=ANONYM_DATE)
                outData.SetEncoding(parameters['BRAINVISION']['Encoding'])
                outData.SetDataFormat(parameters['BRAINVISION']['DataFormat'])
                outData.SetEndian(parameters['BRAINVISION']['Endian'] 
                                  == "Little")
                outData.AddFrequency(recording.Frequency)

                Logger.info("Creating eeg.vhdr header file")
                for ch in channels:
                    outData.Header.Channels.append(
                            BvChannel(Base=ch,
                                      Comments=ch.SigMainType 
                                      + "-" + ch.SigSubType))
                outData.Header.write()

                Logger.info("Creating eeg.vmrk markers file")
                outData.MarkerFile.OpenFile(outData.GetEncoding())
                outData.MarkerFile.SetFrequency(outData.GetFrequency())
                outData.MarkerFile.SetStartTime(t_ref)
                Logger.info("Writting proper events")
                outData.MarkerFile.AddMarker("New Segment", t_ref, 0, -1, "")
                for ev in events:
                    if (ev.GetChannelsSize() == 0)\
                       or parameters.getboolean("EVENTS","MergeCommonEvents"):
                        outData.MarkerFile.AddMarker(
                                ev.GetName(ToReplace=(",", "\1")),
                                ev.GetTime(),
                                ev.GetDuration(), -1, "")
                    else:
                        for c in ev.GetChannels():
                            outData.MarkerFile.AddMarker(
                                    ev.GetName(ToReplace=(",","\1")), 
                                    ev.GetTime(), ev.GetDuration(), 
                                    channels.index(
                                        recording.GetChannelById(c)),
                                    "")
                outData.MarkerFile.Write()

                Logger.info("Creating eeg data file")
                outData.DataFile.SetDataFormat(
                        outData.Header.BinaryInfo.BinaryFormat)
                outData.DataFile.SetEndian(
                        outData.Header.BinaryInfo.UseBigEndianOrder)
                outData.DataFile.OpenFile()
                t_e = t_ref
                t_count = 1

                mem_used = process.memory_info().rss
                mem_remained = mem_requested - mem_used
                t_step = int(mem_remained / mem_1s)
                Logger.debug(
                        "Memory: used: {}, requested: {}, remined: {}".format(
                            tools.humanbytes(mem_used), 
                            tools.humanbytes(mem_requested),
                            tools.humanbytes(mem_remained)))
                Logger.debug("1s time worth: {}"
                             .format(tools.humanbytes(mem_1s)))
                Logger.debug("Time step:{}"
                             .format(timedelta(seconds=t_step)))
                while True:
                    t_s = t_e
                    t_e = t_e + timedelta(0,t_step,0)
                    if t_s >= t_end: break
                    if t_e > t_end: 
                        t_e = t_end
                        t_step = (t_e - t_s).total_seconds()
                    Logger.info("Timepoint {}: Duration {}"
                                .format(t_count,t_e - t_s))
                    Logger.debug("From {} to {} ({})sec."
                                 .format(t_s.isoformat(),
                                         t_e.isoformat(), 
                                         (t_e - t_s).total_seconds()))
                    l_data = []
                    for ch in channels:
                        l_data.append(ch.GetValueVector(
                            t_s, t_e, 
                            freq_mult=ch.GetFrequencyMultiplyer(),
                            raw=True))

                    if entry_points[4] in plugins:
                        try:
                            result = 0
                            result = plugins[entry_points[4]](
                                    recording,
                                    l_data,
                                    argv_plugin, 
                                    parameters["PLUGINS"])
                            if result != 0:
                                raise Exception(
                                        "Plugin {} returned code {}"
                                        .format(entry_points[4], result))
                        except Exception:
                            ex_code = 100 + 40 + result
                            raise

                    outData.DataFile.WriteBlock(l_data)
                    t_count += 1
                    recording.BIDSvalues["filename"] = "eeg/{}".format(
                        recording.GetPrefix(app="_eeg.vhdr"))
                    recording.BIDSvalues["acq_time"] = t_ref
                file_list.append(recording.BIDSfields
                                 .GetLine(recording.BIDSvalues))

            # EDF part
            elif parameters['GENERAL']['Conversion'] == "EDF":
                if parameters.getboolean('EDF', 'EDFplus'):
                    Logger.info("Converting to EDF+ format")
                else:
                    Logger.info("Converting to EDF format")

                outData = EDF(recording.Path(appdir="eeg"),
                              recording.GetPrefix(),
                              AnonymDate=ANONYM_DATE)
                outData.SetEDFplus(parameters.getboolean('EDF', 'EDFplus'))
                outData.Patient["Code"] = recording.SubjectInfo.ID
                if recording.SubjectInfo.Gender == 1:
                    outData.Patient["Sex"] = "F"
                elif recording.SubjectInfo.Gender == 2: 
                    outData.Patient["Sex"] = "M"
                else :
                    outData.Patient["Sex"] = "X"
                if recording.SubjectInfo.Birth != datetime.min\
                   and ANONYM_BIRTH != "":
                    if ANONYM_BIRTH is not None:
                        outData.Patient["Birthdate"] = ANONYM_BIRTH
                    else :
                        outData.Patient["Birthdate"] =\
                                recording.SubjectInfo.Birth

                outData.Patient["Name"] = recording.SubjectInfo.Name
                outData.Record["StartDate"] = t_ref.replace(microsecond=0)
                outData.Record["Code"] = recording.DeviceInfo.Name
                outData.Record["Equipment"] = recording.DeviceInfo.ID
                outData.SetStartTime(t_ref)
                outData.RecordDuration =\
                    int(parameters["EDF"]["DataRecordDuration"])

                Logger.info("Creating events.edf file")
                for ev in events:
                    if (ev.GetChannelsSize() == 0)\
                            or parameters.getboolean("EVENTS",
                                                     "MergeCommonEvents"):
                        outData.AddEvent(ev.GetName(),
                                         ev.GetTime(),
                                         ev.GetDuration(),
                                         -1, "")
                    else:
                        for c in ev.GetChannels():
                            outData.AddEvent(ev.GetName(),
                                             ev.GetTime(), 
                                             ev.GetDuration(), 
                                             channels.index(
                                             recording.GetChannelById(c)),
                                             "")
                outData.WriteEvents()

                Logger.info("Creating eeg.edf file")
                for ch in channels:
                    outData.Channels.append(
                            EDFChannel(Base=ch,
                                       Type=ch.SigMainType, 
                                       Specs=ch.SigMainType
                                       + "-" + ch.SigSubType,
                                       Filter=""))
                outData.WriteHeader()
                t_e = t_ref

                mem_used = process.memory_info().rss
                mem_remained = mem_requested - mem_used
                t_step = int(mem_remained / mem_1s)
                Logger.debug("Memory: used: {}, requested: {}, remined: {}"
                             .format(tools.humanbytes(mem_used), 
                                     tools.humanbytes(mem_requested),
                                     tools.humanbytes(mem_remained)))
                Logger.debug("Memory expected for 1s: {}"
                             .format(tools.humanbytes(mem_1s)))
                Logger.debug("Time step:{}".format(timedelta(seconds=t_step)))
                if t_step % outData.RecordDuration != 0:
                    t_step = outData.RecordDuration \
                             * (t_step // outData.RecordDuration + 1)
                t_count = 1
                while True:
                    t_s = t_e
                    t_e = t_e + timedelta(0, t_step, 0)
                    if t_s >= t_end: break
                    if t_e > t_end: 
                        t_e = t_end
                        t_step = (t_e - t_s).total_seconds()
                        if t_step % outData.RecordDuration != 0:
                            t_step = outData.RecordDuration \
                                * (t_step // outData.RecordDuration + 1)
                            t_e = t_s + timedelta(0,t_step,0)

                    Logger.info("Timepoint {}: Duration {}"
                                .format(t_count,t_e - t_s))
                    Logger.debug("From {} to {} ({})sec."
                                 .format(t_s.isoformat(),
                                         t_e.isoformat(), 
                                         (t_e - t_s).total_seconds()))
                    l_data = []
                    for ch in channels:
                        l_data.append(
                                ch.GetValueVector(t_s, t_e, 
                                                  freq_mult=1, raw=True))

                    if entry_points[4] in plugins:
                        try:
                            result = 0
                            result = plugins[entry_points[4]](
                                        channels, 
                                        l_data, 
                                        argv_plugin, 
                                        parameters["PLUGINS"])
                            if result != 0:
                                raise Exception(
                                        "Plugin {} returned code {}"
                                        .format(entry_points[4], result))
                        except Exception:
                            ex_code = 100 + 40 + result
                            raise

                    outData.WriteDataBlock(l_data, t_s)
                    t_count += 1
                outData.Close()

                recording.BIDSvalues["filename"] = "eeg/{}".format(
                    recording.GetPrefix(app="_eeg.edf"))
                recording.BIDSvalues["acq_time"] = t_ref
                file_list.append(recording.BIDSfields
                                 .GetLine(recording.BIDSvalues))

            # Matlab SPM12 eeg format
            elif parameters['GENERAL']["Conversion"] == "MEEG":
                Logger.info("Converting to Matlab SPM format")
                outData = MEEG(recording.Path(appdir="eeg"),
                               recording.GetPrefix(),
                               AnonymDate=ANONYM_DATE)
                outData.SetStartTime(t_ref)
                outData.SetDuration((t_end - t_ref).total_seconds())
                outData.AddFrequency(recording.Frequency)
                Logger.info("Creating eeg.mat header file")
                outData.InitHeader()
                for ch in channels:
                    outData.AppendChannel(ch)
                outData.WriteChannels()
                for ev in events:
                    outData.AppendEvent(ev)
                outData.WriteEvents()
                outData.WriteHeader()

                Logger.info("Creating eeg.dat file")
                t_e = t_ref
                t_count = 1

                mem_used = process.memory_info().rss
                mem_remained = mem_requested - mem_used
                t_step = int(mem_remained / mem_1s)
                Logger.debug(
                    "Memory used: {}, Memory requested: {}, Memory remined: {}"
                    .format(tools.humanbytes(mem_used), 
                            tools.humanbytes(mem_requested),
                            tools.humanbytes(mem_remained)))
                Logger.debug("1s time worth: {}"
                             .format(tools.humanbytes(mem_1s)))
                Logger.debug("Time step:{}".format(timedelta(seconds=t_step)))
                while True:
                    t_s = t_e
                    t_e = t_e + timedelta(0,t_step,0)
                    if t_s >= t_end: break
                    if t_e > t_end: 
                        t_e = t_end
                        t_step = (t_e - t_s).total_seconds()
                    Logger.info("Timepoint {}: Duration {}"
                                .format(t_count,t_e - t_s))
                    Logger.debug("From {} to {} ({})sec."
                                 .format(t_s.isoformat(), 
                                         t_e.isoformat(), 
                                         (t_e - t_s).total_seconds()))
                    l_data = []
                    for ch in channels:
                        l_data.append(ch.GetValueVector(
                            t_s, t_e, freq_mult=ch.GetFrequencyMultiplyer()))
                    outData.WriteBlock(l_data)
                    t_count += 1
                recording.BIDSvalues["filename"] = "eeg/{}".format(
                    recording.GetPrefix(app="_eeg.mat"))
                recording.BIDSvalues["acq_time"] = t_ref
                file_list.append(recording.BIDSfields
                                 .GetLine(recording.BIDSvalues))

            # Copiyng original files if there no conversion
            elif parameters['GENERAL']["Conversion"] == "":
                Logger.info("Copying original files")
                for f in recording.GetMainFiles(
                            path=recording.GetInputPath()):
                    Logger.debug("file: " + f)
                    shutil.copy2(
                            recording.GetInputPath(f), 
                            recording.Path(appfile=recording
                                           .GetPrefix(app="_" + f)))
                recording.BIDSvalues["filename"] = "eeg/{}".format(
                    recording.GetPrefix(app="_Recording.esrc"))
                recording.BIDSvalues["acq_time"] = t_ref
                file_list.append(recording.BIDSfields
                                 .GetLine(recording.BIDSvalues))

            else:
                raise Exception("Conversion to {} format not implemented"
                                .format(parameters['GENERAL']["Conversion"]))

            scansName = "sub-" + recording.SubjectInfo.ID
            if recording.GetSession() != "":
                scansName += "_ses-" + recording.GetSession()
            scansName += "_scans"
            scansName = recording.Path() + scansName
            recording.BIDSfields.DumpDefinitions(scansName + ".json")
            with open(scansName + ".tsv", "a", encoding='utf-8') as f:
                for l in file_list:
                    print(l, file=f)

        # Copiyng auxiliary files
        if parameters["BIDS"].getboolean("IncludeAuxiliary"):
            out = recording.Path(predir="auxiliaryfiles",
                                 appdir="eeg")
            tools.create_directory(path=out,
                                   toRemove=recording.GetPrefix(app="*"),
                                   allowDups=parameters["GENERAL"]
                                   .getboolean("OverideDuplicated"))
            Logger.info("Copying auxiliary files. It not BIDS complient!")
            for f in recording.GetAuxFiles(path=recording.GetInputPath()):
                Logger.debug("file: " + f)
                shutil.copy2(recording.GetInputPath(f), 
                             out + recording.GetPrefix(app="_" + f))

        with open(parameters['GENERAL']['OutputFolder'] 
                  + "participants.tsv", "a",
                  encoding='utf-8') as f:
            flib = recording.SubjectInfo.BIDSfields
            fval = recording.SubjectInfo.BIDSvalues
            s_gen = ""
            if recording.SubjectInfo.Gender == 1: 
                s_gen = "F"
            elif recording.SubjectInfo.Gender == 2:
                s_gen = "M"
            fval["participant_id"] = "sub-" + recording.SubjectInfo.ID
            fval["sex"] = s_gen
            if recording.SubjectInfo.Birth != datetime.min:
                s_age = str(time_limits[0][0].year 
                            - recording.SubjectInfo.Birth.year)
                fval["age"] = s_age
            print(flib.GetLine(fval), file=f)

        if not os.path.isfile(parameters['GENERAL']['OutputFolder']
                              + "participants.json"):
            flib.DumpDefinitions(
                    parameters['GENERAL']['OutputFolder'] 
                    + "participants.json")

        # Checking the data_description and README files
        if not os.path.isfile(parameters['GENERAL']['OutputFolder']
                              + "dataset_description.json"):
            Logger.warning("BIDS requires 'dataset_description.json' file \
in output folder.")
        if not os.path.isfile(parameters['GENERAL']['OutputFolder']
                              + "README"):
            Logger.warning("BIDS recommends 'README' file \
in output folder.")

        # Cheking Plugin file
        if len(plugins) != 0:
            if not os.path.isfile(parameters['GENERAL']['OutputFolder']
                                  + "code/" 
                                  + parameters["PLUGINS"]["Plugin"]):
                tools.create_directory(parameters['GENERAL']['OutputFolder']
                                       + "code")
                Logger.info("Copying plugin file to code/")
                shutil.copy2(parameters["PLUGINS"]["Plugin"],
                             parameters['GENERAL']['OutputFolder']
                             + "code/.")

    except Exception as e:
        if ex_code == 0:
            ex_code = 1

        exc_type, exc_value, exc_traceback = os.sys.exc_info()
        tr = traceback.extract_tb(exc_traceback)
        for l in tr:
            Logger.error('File "' + l[0] + '", line '
                         + str(l[1]) + " in " + l[2] + ":")
        Logger.error(type(e).__name__ + ": " + str(e))
        if recording is not None and recording.IsLocked():
            if outData is not None: del outData
            if ex_code // 10 != 1 and ex_code // 100 != 10:
                flist = glob.glob(recording.Path(appdir="eeg")
                                  + recording.GetPrefix(app="*"))
                if len(flist) != 0:
                    for f in flist:
                        tools.rrm(f)
        Logger.info("Command: '" + "' '".join(argv + argv_plugin) + "'")

    try:
        Logger.info(">>>>>>>>>>>>>>>>>>>>>>")
        Logger.info("Took {} seconds".format(tm.process_time()))
        Logger.info("<<<<<<<<<<<<<<<<<<<<<<")
        if recording and recording.IsLocked():
            if ex_code // 10 != 1:
                shutil.copy2(tmpDir + "/logfile",
                             parameters["GENERAL"]["OutputFolder"] 
                             + "sourcedata/log/"
                             + recording.GetPrefix(app=".log"))
                shutil.copy2(tmpDir + "/configuration",
                             parameters["GENERAL"]["OutputFolder"] 
                             + "sourcedata/configuration/"
                             + recording.GetPrefix(app=".ini")) 
                fileHandler.close()
            tools.rrm(tmpDir)
        else:
            Logger.warning("Output path is not defined. See in "
                           + tmpDir + "logfile for more details.")
            fileHandler.close()
    except Exception as e:
        if ex_code == 0:
            ex_code = 20
        Logger.error("Unable to copy files to working directory. See in " 
                     + tmpDir + "logfile for more details.")
        exc_type, exc_value, exc_traceback = os.sys.exc_info()
        tr = traceback.extract_tb(exc_traceback)
        for l in tr:
            Logger.error('File "' + l[0] + '", line '
                         + str(l[1]) + " in " + l[2] + ":")
        Logger.error(type(e).__name__ + ": " + str(e))

    return(ex_code)


def SetupBIDS():
    """
    Convinience function to setup any global BIDS related settings
    """

    # participants fields
    GenericRecord.Subject.BIDSfields.AddField(
            name="participant_id",
            longName="Participant Id",
            description="label identifying a particular subject")
    GenericRecord.Subject.BIDSfields.AddField(
        name="age",
        longName="Age",
        description="Age of a subject",
        units="year")
    GenericRecord.Subject.BIDSfields.AddField(
        name="sex",
        longName="Sex",
        description="Sex of a subject",
        levels={
            "F"   : "Female",
            "M"   : "Male"}
            )

    # scans fields
    GenericRecord.Record.BIDSfields.AddField(
        name="filename",
        longName="File Name",
        description="Path to the scan file")
    GenericRecord.Record.BIDSfields.AddField(
        name="acq_time",
        longName="Acquisition time",
        description="Time corresponding to the first data "
        "taken during the scan")

    # events fields
    GenericEvent.GenEvent.BIDSfields.AddField(
          name="onset", 
          description="Onset (in seconds) of the event measured "
          "from the beginning of the acquisition of "
          "the first volume in the corresponding task imaging "
          "data file. If any acquired scans have been discarded "
          "before forming the imaging data file, ensure that "
          "a time of 0 corresponds to the first image stored.",
          units="s")
    GenericEvent.GenEvent.BIDSfields.AddField(
          name="duration",
          description="Duration of the event (measured from onset) "
          "in seconds. Must always be either zero "
          "or positive. A \"duration\" value of zero "
          "implies that the delta function or event "
          "is so short as to be effectively modeled "
          "as an impulse.",
          units="s")
    GenericEvent.GenEvent.BIDSfields.AddField(
          name="sample",
          description="Onset of the event according to "
          "the sampling scheme of the recorded modality "
          "(i.e., referring to the raw data file that "
          "the events.tsv file accompanies).",
          activated=False)
    GenericEvent.GenEvent.BIDSfields.AddField(
          name="trial_type",
          description="Primary categorisation of each trial "
          "to identify them as instances of the experimental "
          "conditions. For example: for a response inhibition "
          "task, it could take on values \"go\" and \"no-go\" "
          "to refer to response initiation and response inhibition "
          "experimental conditions.")
    GenericEvent.GenEvent.BIDSfields.AddField(
          name="response_time",
          description="Response time measured in seconds. A negative "
          "response time can be used to represent preemptive "
          "responses and \"n/a\" denotes a missed response.",
          units="s",
          activated=False)
    GenericEvent.GenEvent.BIDSfields.AddField(
          name="stim_file",
          description="Represents the location of the stimulus file "
          "(image, video, sound etc.) presented at the given onset "
          "time. There are no restrictions on the file formats of "
          "the stimuli files, but they should be stored in the "
          "/stimuli folder (under the root folder of the dataset; "
          "with optional subfolders). The values under the stim_file "
          "column correspond to a path relative to \"/stimuli\". "
          "For example \"images/cat03.jpg\" will be translated to "
          "\"/stimuli/images/cat03.jpg\".",
          activated=False)
    GenericEvent.GenEvent.BIDSfields.AddField(
          name="value",
          description="Marker value associated with the event (e.g., "
          "the value of a TTL trigger that was recorded at the onset "
          "of the event).")
    GenericEvent.GenEvent.BIDSfields.AddField(
          name="HED",
          description="Hierarchical Event Descriptor (HED) Tag. "
          "See Appendix III for details.",
          url="https://bids-specification.readthedocs.io/en/latest"
          "/99-appendices/03-hed.html",
          activated=False)
    GenericEvent.GenEvent.BIDSfields.AddField(
          name="channels",
          description="List of channels names that are associated with "
                      "this event")

    GenericChannel.GenChannel.BIDSfields.AddField(
            name="name",
            longName="Channel name",
            description="Channel name (e.g., FC1, Cz)")
    GenericChannel.GenChannel.BIDSfields.AddField(
            name="type",
            longName="Type of channel",
            description="Type of channel; must be one of the type "
            "listed there: \n"
            "https://bids-specification.readthedocs.io/en/latest/"
            "04-modality-specific-files/03-electroencephalography.html")
    GenericChannel.GenChannel.BIDSfields.AddField(
            name="units",
            longName="Measurement units",
            description="Physical unit of the data values recorded by "
            "this channel in SI units (see Appendix V: Units for allowed "
            "symbols of BIDS):\n"
            "https://bids-specification.readthedocs.io/en/latest/"
            "99-appendices/05-units.html")
    GenericChannel.GenChannel.BIDSfields.AddField(
            name="description",
            longName="Description of channel",
            description="Free-form text description of the channel, "
            "or other information of interest. "
            "Here original channel name and type.")
    GenericChannel.GenChannel.BIDSfields.AddField(
            name="sampling_frequency",
            longName="Channel's sampling frequency",
            description="Sampling rate of the channel in Hz.",
            units="Hz")
    GenericChannel.GenChannel.BIDSfields.AddField(
            name="reference",
            longName="Channel used as reference",
            description="Name of the reference electrode(s) (not needed when "
            "it is common to all channels, in that case it can be specified "
            "in *_eeg.json as EEGReference).",
            activated=False)
    GenericChannel.GenChannel.BIDSfields.AddField(
            name="low_cutoff",
            longName="Low passing band cut-off",
            description="Frequencies used for the high-pass filter applied "
            "to the channel in Hz.",
            units="Hz",
            activated=False)
    GenericChannel.GenChannel.BIDSfields.AddField(
            name="high_cutoff",
            longName="High passing band cut-off",
            description="Frequencies used for the low-pass filter applied "
            "to the channel in Hz. Note that hardware anti-aliasing "
            "in A/D conversion of all EEG electronics applies a low-pass "
            "filter; specify its frequency here if applicable.",
            units="Hz",
            activated=False)
    GenericChannel.GenChannel.BIDSfields.AddField(
            name="notch",
            longName="Notch filter",
            description="Frequencies used for the notch filter applied to "
            "the channel, in Hz.",
            units="Hz",
            activated=False)
    GenericChannel.GenChannel.BIDSfields.AddField(
            name="status",
            longName="Status of the channel",
            description="Data quality observed on the channel (good/bad). "
            "A channel is considered bad if its data quality is compromised "
            "by excessive noise. Description of noise type SHOULD "
            "be provided in [status_description].",
            levels={"good": "a good channel", "bad": "noisy channel"},
            activated=False)
    GenericChannel.GenChannel.BIDSfields.AddField(
            name="status_description",
            longName="Descroption of the status",
            description="Free-form text description of noise or artifact "
            "affecting data quality on the channel. It is meant to explain "
            "why the channel was declared bad in [status].",
            activated=False)


if __name__ == "__main__":
    os.sys.exit(main(os.sys.argv))
