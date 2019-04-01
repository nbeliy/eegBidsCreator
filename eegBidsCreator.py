import logging
import os
import json
import glob
import olefile
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
import tools.json as tjson

from Parcel.parcel import Parcel
from DataStructure.Generic.Record import Record as GRecord
from DataStructure.Generic.Event import GenEvent

from DataStructure.SPM12.MEEG import MEEG

from DataStructure.Embla.Record import ParceRecording
from DataStructure.Embla.Channel import EbmChannel

from DataStructure.BrainVision.BrainVision import BrainVision
from DataStructure.BrainVision.Channel import BvChannel

from DataStructure.EDF.EDF import EDF
from DataStructure.EDF.EDF import Channel as EDFChannel


VERSION = 'dev0.72r1'


def main(argv):

    process = psutil.Process(os.getpid())
    recording = None
    outData = None

    argv_plugin = None
    if '--' in argv:
        argv_plugin = argv[argv.index('--') + 1:]
        argv = argv[:argv.index('--')]

    ex_code = 0
    args = cli.parce_CLI(argv[1:], VERSION)

    parameters = cfi.default_parameters()
    if args.config_file:
        cfi.read_parameters(parameters, args.config_file[0])

    # Overloading values by command-line arguments
    if args.ses is not None: 
        parameters['GENERAL']['SessionId'] = args.ses
    if args.task is not None:
        parameters['GENERAL']['TaskId'] = args.task
    if args.acq is not None:
        parameters['GENERAL']['AcquisitionId'] = args.acq
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

    eegform = None
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
    extension = os.path.splitext(basename)[1]
    try:
        if not os.path.exists(parameters['GENERAL']['Path']):
            raise Exception(
                "Path {} is not valid".format(parameters['GENERAL']['Path']))
        if os.path.isdir(parameters['GENERAL']['Path']):
            if len(glob.glob(parameters['GENERAL']['Path'] + '*.ebm')) > 0:
                eegform = "embla"
        elif extension == '.edf':
            eegform = "edf"
        else:
            raise Exception("Unable determine eeg format")

        Logger.info("Output: {}".format(parameters['GENERAL']['OutputFolder']))
        if not os.path.isdir(parameters['GENERAL']['Path']):
            raise Exception(
                "Path {} is not valid".format(parameters['GENERAL']['Path']))

        recording = GRecord()
        recording.SetOutputPath(parameters['GENERAL']['OutputFolder'])

        if eegform == "embla":
            Logger.info("Detected {} format".format(eegform))
            recording._extList = \
                [".ebm",".ead",".esedb",".ewp",".esrc",".esev"]
            if len(glob.glob(parameters['GENERAL']['Path']
                   + 'Recording.esrc')) != 1:
                raise FileNotFoundError(
                    "Couldn't find Recording.escr file, "
                    "needed for recording proprieties")
            if len(glob.glob(parameters['GENERAL']['Path'] + '*.esedb')) == 0:
                Logger.warning("No .esedb files containing events found. "
                               "Event list will be empty.")
            # Reading metadata
            esrc = olefile.OleFileIO(
                parameters['GENERAL']['Path'] + 'Recording.esrc').\
                openstream('RecordingXML')
            xml = esrc.read().decode("utf_16_le")[2:-1]
            metadata = ParceRecording(xml)

            recording.SetId(session=parameters['GENERAL']["SessionId"], 
                            task=parameters['GENERAL']["TaskId"],
                            acquisition=parameters['GENERAL']["AcquisitionId"])

            birth = datetime.min
            if "DateOfBirth" in metadata["PatientInfo"]:
                birth = metadata["PatientInfo"]["DateOfBirth"]

            recording.SetSubject(id=metadata["PatientInfo"]["ID"],
                                 name="",
                                 birth=birth,
                                 gender=metadata["PatientInfo"]["Gender"],
                                 notes=metadata["PatientInfo"]["Notes"],
                                 height=metadata["PatientInfo"]["Height"],
                                 weight=metadata["PatientInfo"]["Weight"])
            recording.SetDevice(type=metadata["Device"]["DeviceTypeID"],
                                id=metadata["Device"]["DeviceID"],
                                name=metadata["Device"]["DeviceName"],
                                manufactor="RemLogic")
            recording.SetStartTime(metadata["RecordingInfo"]["StartTime"],
                                   metadata["RecordingInfo"]["StopTime"])
            esrc.close()

        else:
            raise Exception(
                    "EEG format {} not implemented (yet)".format(eegform))

        if entry_points[0] in plugins:
            try:
                result = 0
                result = plugins[entry_points[0]](
                        recording, 
                        argv_plugin,
                        parameters.items("PLUGINS"))
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

        recording.Lock()

        tools.create_directory(
                path=recording.Path(),
                toRemove=recording.Prefix(app="*"),
                allowDups=parameters["GENERAL"]
                .getboolean("OverideDuplicated"))

        tools.create_directory(
                path=parameters['GENERAL']['OutputFolder'] 
                + "sourcedata/log",
                toRemove=recording.Prefix(app=".log"),
                allowDups=True)

        tools.create_directory(
                path=parameters['GENERAL']['OutputFolder'] 
                + "sourcedata/configuration",
                toRemove=recording.Prefix(app=".ini"),
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
            if extension == "":
                shutil.copytree(parameters['GENERAL']['Path'],
                                srcPath + basename)
            else:
                shutil.copy2(parameters['GENERAL']['Path'],
                             srcPath + basename)

        t_ev_min = datetime.max
        t_ev_max = datetime.min

        if not recording.GetStartTime():
            Logger.warning("Unable to get StartTime of record. "
                           "Will be set to first data point.")
        if not recording.GetStopTime():
            Logger.warning("Unable to get EndTime of record. "
                           "Will be set to last data point.")

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

        if eegform == "embla":
            channels = [EbmChannel(c) for c in
                        glob.glob(parameters['GENERAL']['Path'] + "*.ebm")]
        else:
            raise Exception(
                    "EEG format {} not implemented (yet)".format(eegform))

        recording.AddChannels(channels,
                              white_list=to_keep,
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
                        parameters.items("PLUGINS"))
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
        if t_l or t_h:
            t_l, t_h = recording.CropTime(t_l, t_h)
            if t_l != t_ref:
                Logger.info("Cropping start time by {}".format(t_l - t_ref))
                t_ref = t_l
            if t_h != t_end:
                Logger.info("Cropping end time by {}".format(t_end - t_h))
                t_end = t_h
            Logger.info("New duration: {}".format(t_end - t_ref))

        Logger.info("Reading events info")
        to_keep = []
        if parameters['EVENTS']['WhiteList'] != '':
            to_keep = [p.strip() 
                       for p in parameters['EVENTS']['WhiteList'].split(',')]
        to_drop = []
        if parameters['EVENTS']['BlackList'] != '':
            to_drop = [p.strip() 
                       for p in parameters['EVENTS']['BlackList'].split(',')]

        if eegform == "embla":
            for evfile in glob.glob(parameters['GENERAL']['Path'] + "*.esedb"):
                esedb = olefile.OleFileIO(evfile)\
                        .openstream('Event Store/Events')
                root = Parcel(esedb)
                evs = root.get("Events")
                aux_l = root.getlist("Aux Data")[0]
                grp_l = root.getlist("Event Types")[0].getlist()
                times = root.getlist("EventsStartTimes")[0]
                locat = root.get("Locations", 0)

                for ev,time in zip(evs, times):
                    ch_id = locat.getlist("Location")[ev.LocationIdx]\
                            .get("Signaltype").get("MainType")
                    ch_id += "_" + locat.getlist("Location")[ev.LocationIdx]\
                             .get("Signaltype").get("SubType")

                    try:
                        name = grp_l[ev.GroupTypeIdx]
                    except LookupError:
                        try:
                            name = aux_l.get("Aux", ev.AuxDataID)\
                                   .get("Sub Classification History")\
                                   .get("1").get("type")
                        except Exception:
                            Logger.warning(
                                    "Can't get event name for index {}"
                                    .format(ev.AuxDataID))
                            name = ""

                    if to_keep:
                        if name not in to_keep: continue
                    if to_drop:
                        if name in to_drop: continue

                    evnt = GenEvent(Name=name, Time=time, Duration=ev.TimeSpan)
                    evnt.AddChannel(ch_id)
                    recording.AddEvents(evnt)

                    if parameters["DATATREATMENT"]["StartEvent"] == name\
                            and time < t_ev_min:
                        t_ev_min = time
                        Logger.info(
                                "Cropping start time by {} from event {}"
                                .format(time - t_ref, name))
                    if parameters["DATATREATMENT"]["EndEvent"] == name\
                            and time > t_ev_max:
                        t_ev_max = time
                        Logger.info(
                                "Cropping end time by {} from event {}"
                                .format(t_end - time, name))
                esedb.close()
        else:
            raise Exception(
                    "EEG format {} not implemented (yet)".format(eegform))

        # Treating events
        if t_ev_min or t_ev_max:
            t_ev_min, t_ev_max = recording.CropTime(t_ev_min, t_ev_max)
            if t_ev_min != t_ref:
                Logger.info(
                        "Cropping start time by {}"
                        .format(t_ev_min - t_ref))
                t_ref = t_ev_min
            if t_ev_max != t_end:
                Logger.info(
                        "Cropping end time by {}"
                        .format(t_end - t_ev_max))
                t_end = t_ev_max
            Logger.info("New duration: {}".format(t_end - t_ref))

        if parameters.getboolean("EVENTS","IncludeSegmentStart"):
            if recording.GetMainChannel():
                main_channel = recording.GetMainChannel()
                for t in range(0, main_channel.GetNsequences()):
                    ev = GenEvent(Name="New Segment", 
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
                result = plugins[entry_points[2]](recording,
                                                  argv_plugin,
                                                  parameters.items("PLUGINS"))
                if result != 0:
                    raise Exception(
                            "Plugin {} returned code {}"
                            .format(entry_points[2], result))
            except Exception:
                ex_code = 100 + 20 + result
                raise

        Logger.info("Creating eeg.json file")
        with open(recording.Path()
                  + recording.Prefix(app="_eeg.json"),
                  "w",
                  encoding='utf-8') as f:
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
            json.dump(recording.JSONdata, f, 
                      skipkeys=False, indent="  ", 
                      separators=(',',':'))

        # Updating channels frequency multiplier and starting time
        for c in recording.Channels:
            c.SetFrequencyMultiplyer(int(
                recording.Frequency / c.GetFrequency()))

        time_limits = None
        if parameters["RUNS"]["SplitRuns"] == "Channel":
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
        else: time_limits = [[t_ref, t_end]]

        if len(time_limits) == 0:
            raise Exception("No valid runs found")

        if entry_points[3] in plugins:
            try:
                result = 0
                result = plugins[entry_points[3]](
                         recording,
                         time_limits,
                         argv_plugin,
                         parameters.items("PLUGINS"))
                if result != 0:
                    raise Exception(
                            "Plugin {} returned code {}"
                            .format(entry_points[3], result))
            except Exception:
                ex_code = 100 + 30 + result
                raise

        # Running over runs
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
            run = None
            if parameters["RUNS"]["SplitRuns"] != "":
                run = count + 1
                Logger.info("Run {}: duration: {}".format(run, t_end - t_ref))

            Logger.info("Creating channels.tsv file")
            with open(recording.Path()
                      + recording.Prefix(run=run, app="_channels.tsv"),
                      "w", 
                      encoding='utf-8') as f:
                print("name",
                      "type",
                      "units",
                      "description", 
                      "sampling_frequency",
                      "reference", 
                      sep='\t', file=f)
                for c in channels:
                    print(c.GetName(Void="n/a"),
                          c.GetType(Void="n/a"),
                          c.GetUnit(Void="n/a"),
                          c.GetDescription(Void="n/a"),
                          c.GetFrequency(), 
                          c.GetReference(Void="n/a"), 
                          sep="\t", file=f)

            tjson.eventsJson(recording.Path()
                             + recording.Prefix(run=run, 
                                                app="_events.json"))
            Logger.info("Creating events.tsv file")     
            with open(recording.Path()
                      + recording.Prefix(run=run,app="_events.tsv"),
                      "w", encoding='utf-8') as f:
                print("onset", 
                      "duration",
                      "trial_type", 
                      "responce_time",
                      "value",
                      "channels",
                      sep='\t', file=f)
                for ev in events:
                    if ev.GetChannelsSize() == 0\
                       or parameters.getboolean("EVENTS","MergeCommonEvents"):
                        print("%.3f\t%.2f\t%s\tn/a\tn/a" 
                              % (ev.GetOffset(t_ref),
                                 ev.GetDuration(), 
                                 ev.GetName(Void="n/a", ToReplace=("\t"," "))),
                              end="", file=f)
                        ch_list = "\t"
                        if ev.GetChannelsSize() == 0:
                            ch_list += "n/a"
                        else:
                            for c_id in ev.GetChannels():
                                ch = recording.GetChannelById(c_id)
                                ch_list += ch.GetName(Void="n/a",
                                                      ToReplace=("\t"," "))

                                ch_list += ","
                        print(ch_list, file=f)
                    else :
                        for c_id in ev.GetChannels():
                            print("%.3f\t%.2f\t%s\tn/a\tn/a\t%s" 
                                  % (ev.GetOffset(t_ref), 
                                     ev.GetDuration(), 
                                     ev.GetName(Void="n/a",
                                                ToReplace=("\t"," ")),
                                     recording.GetChannelById(c_id)
                                              .GetName(Void="n/a", 
                                                       ToReplace=("\t"," "))),
                                  file=f)

            # BV format
            if parameters['GENERAL']['Conversion'] == "BV":
                Logger.info("Converting to BrainVision format")
                outData = BrainVision(recording.Path(),
                                      recording.Prefix(run=run),
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
                        if outData.Header.BinaryInfo.BinaryFormat\
                           == "IEEE_FLOAT_32":
                            l_data.append(ch.GetValueVector(
                                t_s, t_e, 
                                freq_mult=ch.GetFrequencyMultiplyer()))
                        else:
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
                                    parameters.items("PLUGINS"))
                            if result != 0:
                                raise Exception(
                                        "Plugin {} returned code {}"
                                        .format(entry_points[4], result))
                        except Exception:
                            ex_code = 100 + 40 + result
                            raise

                    outData.DataFile.WriteBlock(l_data)
                    t_count += 1
                file_list.append("eeg/{}\t{}".format(
                        recording.Prefix(run=run,app="_eeg.vhdr"), 
                        t_ref.isoformat()))

            # EDF part
            elif parameters['GENERAL']['Conversion'] == "EDF":
                Logger.info("Converting to EDF+ format")
                outData = EDF(recording.Path(),
                              recording.Prefix(run=run),
                              AnonymDate=ANONYM_DATE)
                outData.Patient["Code"] = metadata["PatientInfo"]["ID"]
                if "Gender" in metadata["PatientInfo"]:
                    if metadata["PatientInfo"]["Gender"] == 1:
                        outData.Patient["Sex"] = "F"
                    else: 
                        outData.Patient["Sex"] = "M"
                if recording.SubjectInfo.Birth != datetime.min\
                   and ANONYM_BIRTH != "":
                    if ANONYM_BIRTH is not None:
                        outData.Patient["Birthdate"] = ANONYM_BIRTH
                    else :
                        outData.Patient["Birthdate"] =\
                                metadata["PatientInfo"]["DateOfBirth"].date()

                outData.Patient["Name"] = recording.SubjectInfo.Name
                outData.Record["StartDate"] = t_ref.replace(microsecond=0)
                outData.Record["Code"] = metadata["RecordingInfo"]["Type"]
                outData.Record["Equipment"] = metadata["Device"]["DeviceID"]
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
                                        channels, l_data, argv_plugin, 
                                        parameters.items("PLUGINS"))
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

                file_list.append("eeg/{}\t{}".format(
                        recording.Prefix(run=run,app="_eeg.edf"), 
                        t_ref.isoformat()))

            # Matlab SPM12 eeg format
            elif parameters['GENERAL']["Conversion"] == "MEEG":
                Logger.info("Converting to Matlab SPM format")
                outData = MEEG(recording.Path(),
                               recording.Prefix(run=run),
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
                file_list.append("eeg/{}\t{}".format(
                        recording.Prefix(run=run,app="_eeg.mat"), 
                        t_ref.isoformat()))

            # Copiyng original files if there no conversion
            elif parameters['GENERAL']["Conversion"] == "":
                Logger.info("Copying original files")
                for f in recording.GetMainFiles(
                            path=parameters['GENERAL']['Path']):
                    Logger.debug("file: " + f)
                    shutil.copy2(
                            parameters['GENERAL']['Path'] + f, 
                            recording.Path(appendix=recording
                                           .Prefix(app="_" + f)))
                file_list.append("eeg/{}\t{}".format(
                            recording.Prefix(run=run,app="_Recording.esrc"),
                            t_ref.isoformat()))

            else:
                raise Exception("Conversion to {} format not implemented"
                                .format(parameters['GENERAL']["Conversion"]))

            scansName = "sub-" + recording.SubjectInfo.ID
            if recording.GetSession() != "":
                scansName += "_ses-" + recording.GetSession()
            scansName += "_scans.tsv"
            with open(recording.Path(appendix="")
                      + scansName,
                      "a",
                      encoding='utf-8') as f:
                for l in file_list:
                    print(l, file=f)

        # Copiyng auxiliary files
        if parameters["BIDS"].getboolean("IncludeAuxiliary"):
            out = recording.Path(prefix="auxiliaryfiles")
            tools.create_directory(path=out,
                                   toRemove=recording.Prefix(app="*"),
                                   allowDups=parameters["GENERAL"]
                                   .getboolean("OverideDuplicated"))
            Logger.info("Copying auxiliary files. It not BIDS complient!")
            for f in recording.GetAuxFiles(path=parameters['GENERAL']['Path']):
                Logger.debug("file: " + f)
                shutil.copy2(parameters['GENERAL']['Path'] + f, 
                             out + recording.Prefix(app="_" + f))

        with open(parameters['GENERAL']['OutputFolder'] 
                  + "participants.tsv", "a",
                  encoding='utf-8') as f:
            s_id = recording.SubjectInfo.ID
            s_gen = "n/a"
            if recording.SubjectInfo.Gender == 1: 
                s_gen = "F"
            elif recording.SubjectInfo.Gender == 2:
                s_gen = "M"
            s_age = "n/a"
            if recording.SubjectInfo.Birth != datetime.min:
                s_age = str(time_limits[0][0].year 
                            - recording.SubjectInfo.Birth.year)
            print("{}\t{}\t{}".format(s_id, s_gen, s_age), file=f)
        if not os.path.isfile(parameters['GENERAL']['OutputFolder'] 
                              + "participants.json"):
            tjson.participantsJson(
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
            flist = glob.glob(recording.Path()
                              + recording.Prefix(app="*"))
            if len(flist) != 0:
                for f in flist:
                    tools.rrm(f)
        Logger.info("Command: '" + "' '".join(argv) + "'")

    try:
        Logger.info(">>>>>>>>>>>>>>>>>>>>>>")
        Logger.info("Took {} seconds".format(tm.process_time()))
        Logger.info("<<<<<<<<<<<<<<<<<<<<<<")
        if recording and recording.IsLocked():
            shutil.copy2(tmpDir + "/logfile",
                         parameters["GENERAL"]["OutputFolder"] 
                         + "sourcedata/log/"
                         + recording.Prefix(app=".log"))
            shutil.copy2(tmpDir + "/configuration",
                         parameters["GENERAL"]["OutputFolder"] 
                         + "sourcedata/configuration/"
                         + recording.Prefix(app=".ini")) 
            fileHandler.close()
            tools.rrm(tmpDir)
        else:
            Logger.warning("Output path is not defined. See in "
                           + tmpDir + "logfile for more details.")
            fileHandler.close()
    except Exception as e:
        if ex_code == 0:
            ex_code = 10
        Logger.error("Unable to copy files to working directory. See in " 
                     + tmpDir + "logfile for more details.")
        exc_type, exc_value, exc_traceback = os.sys.exc_info()
        tr = traceback.extract_tb(exc_traceback)
        for l in tr:
            Logger.error('File "' + l[0] + '", line '
                         + str(l[1]) + " in " + l[2] + ":")
        Logger.error(type(e).__name__ + ": " + str(e))

    return(ex_code)


if __name__ == "__main__":
    os.sys.exit(main(os.sys.argv))
