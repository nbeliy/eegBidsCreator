VERSION = '0.65r1'

import logging, argparse, os, json, glob, olefile, traceback, struct, configparser
import tempfile, bisect
from datetime import datetime, timedelta
import time as tm
import importlib.util
import inspect

from  Parcel.parcel import Parcel
from DataStructure.Generic.Record import Record as GRecord
from DataStructure.Generic.Event  import GenEvent


from DataStructure.Embla.Record  import ParceRecording
from DataStructure.Embla.Channel import EbmChannel

from DataStructure.BrainVision.BrainVision import BrainVision
from DataStructure.BrainVision.Channel  import BvChannel

from DataStructure.EDF.EDF import EDF
from DataStructure.EDF.EDF import Channel as EDFChannel

import shutil
import psutil



def rmdir(path):
    if os.path.isfile(path):
        os.remove(path)
    else:
        for root, dirs, files in os.walk(path):
            for f in files:
                os.remove(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))

def humanbytes(B):
   'Return the given bytes as a human friendly KB, MB, GB, or TB string'
   B = float(B)
   KB = float(1024)
   MB = float(KB ** 2) # 1,048,576
   GB = float(KB ** 3) # 1,073,741,824
   TB = float(KB ** 4) # 1,099,511,627,776

   if B < KB:
      return '{0} {1}'.format(B,'Bytes' if 0 == B > 1 else 'Byte')
   elif KB <= B < MB:
      return '{0:.2f} KB'.format(B/KB)
   elif MB <= B < GB:
      return '{0:.2f} MB'.format(B/MB)
   elif GB <= B < TB:
      return '{0:.2f} GB'.format(B/GB)
   elif TB <= B:
      return '{0:.2f} TB'.format(B/TB)


def main(argv):
    process = psutil.Process(os.getpid())
    recording=None

    argv_plugin = None
    if '--' in argv:
        argv_plugin = argv[argv.index('--')+1:]
        argv = argv[:argv.index('--')]

    ex_code = 0
    parser = argparse.ArgumentParser(description='Converts EEG file formats to BID standard')

    parser.add_argument('infile', 
        metavar='eegfile', nargs = 1,
        help='input eeg file')
    parser.add_argument('-a, --acquisition', metavar='acqId', dest='acq', help='Id of the acquisition')
    parser.add_argument('-t, --task', metavar='taskId', dest='task', help='Id of the task')
    parser.add_argument('-s, --session', metavar='sesId', dest='ses', help='Id of the session')
    parser.add_argument('-j, --json', metavar='eegJson', dest='eegJson', help="A json file with task description")
    parser.add_argument('-o, --output', nargs=1, dest='outdir', help='destination folder')
    parser.add_argument('-c, --config', nargs=1, dest='config_file', help="Path to configuration file")
    parser.add_argument('--logfile', nargs=1, metavar='log.out', dest='logfile', help='log file destination')
    parser.add_argument('-q,--quiet', dest='quiet', action="store_true", help="Supress standard output")
    parser.add_argument('--log', dest='loglevel', choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help='logging level')
    parser.add_argument('--version', action='version', version='%(prog)s '+VERSION)
    parser.add_argument('--conversion', dest="conv", choices=["EDF","BV"], help="performs conversion to given format")

    args = parser.parse_args(argv[1:])

    parameters = configparser.ConfigParser()
    #Making keys case-sensitive
    parameters.optionxform = lambda option: option
    #Setting up default values
    parameters['GENERAL'] = {
                            "SessionId"     :"", 
                            "TaskId"        :"", 
                            "AcquisitionId" :"",
                            "JsonFile"      :"", 
                            "OutputFolder"  :".", 
                            "Conversion"    :"",
                            "CopySource"    :"yes",
                            "MemoryUsage"   :"2"
                            }
    parameters['LOGGING'] = {
                            "LogLevel"  :"INFO", 
                            "LogFile"   :"",
                            "Quiet"     :"no",
                            "SplitRuns" :"no"
                            }
    parameters['DATATREATMENT'] =   {
                                    "DropChannels"  :"", 
                                    "StartTime"     :"", "EndTime"  :"", 
                                    "StartEvent"    :"", "EndEvent" :"",
                                    "IgnoreOutOfTimeEvents" :"yes",
                                    "IncludeSegmentStart"   :"no",
                                    "MergeCommonEvents"     :"yes",
                                    }
    parameters['RUNS'] =    {
                            "SplitRuns"     :"no",
                            "MainChannel"   :"", 
                            "MinSpan"       :"0"
                            }
    parameters['ANONYMIZATION'] =   {
                                    "Anonymize" :"yes",
                                    "StartDate" :"1973-3-01",
                                    "SubjName"  :"John Doe",
                                    "BirthDate" :""
                                    }
    parameters['PLUGINS']       =   {
                                    "Plugin" : ""
                                    }
    parameters['BRAINVISION']   =   {
                                    "Encoding"  :"UTF-8", 
                                    "DataFormat":"IEEE_FLOAT_32", 
                                    "Endian"    :"Little"
                                    }
    parameters['EDF'] = {
                        "DataRecordDuration"    :"10"
                        }

    #Reading configuration file
    if args.config_file != None:
        readed = parameters.read(args.config_file[0])
        if len(readed) == 0:
            raise FileNotFoundError("Unable to open file "+args.config_file)

    #Overloading values by command-line arguments
    if args.ses      != None: parameters['GENERAL']['SessionId']    = args.ses
    if args.task     != None: parameters['GENERAL']['TaskId']       = args.task
    if args.acq      != None: parameters['GENERAL']['AcquisitionId']= args.acq
    if args.eegJson  != None: parameters['GENERAL']['JsonFile']     = args.eegJson
    if args.conv     != None: parameters['GENERAL']['Conversion']   = args.conv
    if args.infile   != None: parameters['GENERAL']['Path']         = os.path.realpath(args.infile[0])
    if args.outdir   != None: parameters['GENERAL']['OutputFolder'] = os.path.realpath(args.outdir[0])
    if args.loglevel != None: parameters['LOGGING']['LogLevel']     = args.loglevel
    if args.logfile  != None: parameters['LOGGING']['LogFile']      = args.logfile[0]
    if args.quiet    == True: parameters['LOGGING']['Quiet']        = 'yes'

    if parameters['GENERAL']['OutputFolder'][-1] != '/': parameters['GENERAL']['OutputFolder'] += '/'
    if parameters['GENERAL']['Path'][-1] != '/': parameters['GENERAL']['Path'] += '/'

    eegform = None

    '''
    Setup logging.
    Logfile will be stored into temporary directory first, then moved to output directory.
    '''
    tmpDir = tempfile.mkdtemp(prefix=argv[0].replace("/","_")+"_")+"/"

    #logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s", datefmt='%m/%d/%Y %H:%M:%S')
    logFormatter = logging.Formatter("[%(levelname)-7.7s]:%(asctime)s:%(name)s %(message)s", datefmt='%m/%d/%Y %H:%M:%S')
    Logger = logging.getLogger()
    Logger.setLevel(getattr(logging, parameters['LOGGING']['LogLevel'], None))

    fileHandler = logging.FileHandler(tmpDir+"logfile")
    fileHandler.setFormatter(logFormatter)
    Logger.addHandler(fileHandler)

    if parameters['LOGGING']['LogFile'] != "":
        fileHandler2 = logging.FileHandler(parameters['LOGGING']['LogFile'])
        fileHandler2.setFormatter(logFormatter)
        Logger.addHandler(fileHandler2)
        

    if not parameters['LOGGING'].getboolean('Quiet'):
        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(logFormatter)
        Logger.addHandler(consoleHandler)

    ANONYM_DATE = None
    ANONYM_NAME = None
    ANONYM_BIRTH= None
    if parameters.getboolean("ANONYMIZATION","Anonymize"):
        if parameters["ANONYMIZATION"]["StartDate"] != "None" and parameters["ANONYMIZATION"]["StartDate"] != "":
            ANONYM_DATE = datetime.strptime(parameters["ANONYMIZATION"]["StartDate"],"%Y-%m-%d")
        if parameters["ANONYMIZATION"]["SubjName"] != "None":
            ANONYM_NAME = parameters["ANONYMIZATION"]["SubjName"]
        if parameters["ANONYMIZATION"]["BirthDate"] != "None":
            if parameters["ANONYMIZATION"]["BirthDate"] == "" :
                ANONYM_BIRTH = ""
            else:
                ANONYM_BIRTH =  datetime.strptime(parameters["ANONYMIZATION"]["BirthDate"],"%Y-%m-%d")

    entry_points = ["RecordingEP", "ChannelsEP", "EventsEP", "RunsEP", "DataEP"]
    plugins = dict()
    pl_name = ""
    if parameters["PLUGINS"]["Plugin"] != "":
        if not os.path.exists(parameters["PLUGINS"]["Plugin"]):
            raise FileNotFoundError("Plug-in file {} not found".format(parameters["PLUGINS"]["Plugin"]))
        pl_name = os.path.splitext(os.path.basename(parameters["PLUGINS"]["Plugin"]))[0]
        Logger.info("Loading module {} from {}".format(pl_name, parameters["PLUGINS"]["Plugin"]))
        spec = importlib.util.spec_from_file_location(pl_name, parameters["PLUGINS"]["Plugin"])
        if spec == None:
            raise Exception("Unable to load module {} from {}".format(pl_name, parameters["PLUGINS"]["Plugin"]))
        itertools = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(itertools)
        f_list = dir(itertools)
        for ep in entry_points:
            if ep in f_list and callable(getattr(itertools,ep)):
                inspect.getargspec(getattr(itertools,ep))[0]#This returns the list of parameters
                Logger.debug("Entry point {} found".format(ep))
                plugins[ep] = getattr(itertools,ep)
        if len(plugins) == 0:
            Logger.warning("Plugin {} loaded but no compatible functions found".format(pl_name))
        


    Logger.info(">>>>>>>>>>>>>>>>>>>>>>")
    Logger.info("Starting new bidsifier")
    Logger.info("<<<<<<<<<<<<<<<<<<<<<<")

    Logger.debug(str(os.sys.argv))
    Logger.debug("Process PID: "+str(os.getpid()))
    Logger.debug("Temporary directory: "+tmpDir)
    with open(tmpDir+"configuration", 'w') as configfile: parameters.write(configfile)

    Logger.info("File: {}".format(parameters['GENERAL']['Path']))
    basename = os.path.basename(parameters['GENERAL']['Path'][0:-1])
    extension= os.path.splitext(basename)[1]
    try:
        if not os.path.exists(parameters['GENERAL']['Path']):
            raise Exception("Path {} is not valid".format(parameters['GENERAL']['Path']))       
        if os.path.isdir(parameters['GENERAL']['Path']):
            if len(glob.glob(parameters['GENERAL']['Path']+'*.ebm')) > 0:
                eegform = "embla"
        elif extension == '.edf':
            eegform = "edf"
        else:
            raise Exception("Unable determine eeg format")
        

        Logger.info("Output: {}".format(parameters['GENERAL']['OutputFolder']))
        if not os.path.isdir(parameters['GENERAL']['Path']):
            raise Exception("Path {} is not valid".format(parameters['GENERAL']['Path']))

        recording = GRecord("")
        
        if eegform == "embla":
            Logger.info("Detected {} format".format(eegform))
            recording._extList = [".ebm",".ead",".esedb",".ewp",".esrc",".esev"]
            if len(glob.glob(parameters['GENERAL']['Path']+'Recording.esrc')) != 1: 
                raise FileNotFoundError("Couldn't find Recording.escr file, needed for recording proprieties")
            if len (glob.glob(parameters['GENERAL']['Path']+'*.esedb')) == 0:
                Logger.warning("No .esedb files containing events found. Event list will be empty.")
            #Reading metadata
            esrc = olefile.OleFileIO(parameters['GENERAL']['Path']+'Recording.esrc').openstream('RecordingXML')
            xml  = esrc.read().decode("utf_16_le")[2:-1]
            metadata = ParceRecording(xml)

            recording.SetId(session=parameters['GENERAL']["SessionId"], 
                            task=parameters['GENERAL']["TaskId"],
                            acquisition=parameters['GENERAL']["AcquisitionId"])
                        
            birth = datetime.min
            if "DateOfBirth" in metadata["PatientInfo"]:
                birth = metadata["PatientInfo"]["DateOfBirth"]
                
            recording.SetSubject (id = metadata["PatientInfo"]["ID"],
                                name  = "",
                                birth  = birth,
                                gender = metadata["PatientInfo"]["Gender"],
                                notes  = metadata["PatientInfo"]["Notes"],
                                height = metadata["PatientInfo"]["Height"],
                                weight = metadata["PatientInfo"]["Weight"])
            recording.SetDevice(    type=metadata["Device"]["DeviceTypeID"],
                                    id  = metadata["Device"]["DeviceID"],
                                    name= metadata["Device"]["DeviceName"],
                                    manufactor= "RemLogic")
            recording.StartTime = metadata["RecordingInfo"]["StartTime"]
            recording.StopTime  = metadata["RecordingInfo"]["StopTime"]
            esrc.close()
            
            
        else:
            raise Exception("EEG format {} not implemented (yet)".format(eegform))
        
        JSONdata = dict()
        if parameters['GENERAL']['JsonFile'] != "":
            if parameters['GENERAL']['JsonFile'][-5:] != ".json": 
                parameters['GENERAL']['JsonFile'] = os.path.realpath(parameters['GENERAL']['JsonFile']) + recording.GetTask() + ".json"
            Logger.info("JSON File: {}".format(parameters['GENERAL']['JsonFile']))
            with open(parameters['GENERAL']['JsonFile']) as f:
                 JSONdata = json.load(f)
            recording.JSONdata = JSONdata
            if "SamplingFrequency" in recording.JSONdata:
                recording.Frequency = recording.JSONdata["SamplingFrequency"]
            if "TaskName" in recording.JSONdata and recording.JSONdata["TaskName"] != recording.GetTask():
                raise Exception("Task name '{}' in JSON file mismach name in record '{}'".format(recording.JSONdata["TaskName"], recording.GetTask()))
#Entry point Recording_Init
            
        if entry_points[0] in plugins:
            result = plugins[entry_points[0]](recording, argv_plugin, parameters.items("PLUGINS"))
            if result != 0:
                raise Exception("Plugin {} returned code {}".format(entry_points[0], result))

        Logger.info("Patient Id: {}".format(recording.SubjectInfo.ID))
        Logger.info("Session Id: " + recording.GetSession())
        Logger.info("Task    Id: " + recording.GetTask())
        Logger.info("Acq     Id: " + recording.GetAcquisition())

        recording.ResetPrefix()
        recording.ResetPath()
        recording.SetEEGPath(prepath=parameters['GENERAL']['OutputFolder'])
        if os.path.exists(recording.eegPath):
            Logger.debug("Output directory already exists")
            flist = glob.glob(recording.eegPath+recording.Prefix(app="*"))
            if len(flist) != 0:
                Logger.warning("Found {} files with same identification. They will be removed.".format(len(flist)))
                for f in flist:
                    rmdir(f)
        else: 
            Logger.info("Creating output directory {}".format(recording.eegPath))
            os.makedirs(recording.eegPath)
        Logger.info("EEG will be saved in "+recording.eegPath)

        if parameters['GENERAL'].getboolean('CopySource'):
            srcPath = parameters['GENERAL']['OutputFolder']+"sourcedata/"+ recording.Path()+"/"
            if os.path.exists(srcPath):
                if os.path.exists(srcPath+basename):
                    Logger.warning('"{}" exists in sourcedata directory. It will be erased.'.format(basename))
                    rmdir(srcPath+basename)
                    shutil.rmtree(srcPath+basename)
            else:
                Logger.info("Creating output directory {}".format(srcPath))
                os.makedirs(srcPath)
            Logger.info("Copiyng original data to sourcedata folder")
            if extension == "":
                shutil.copytree(parameters['GENERAL']['Path'], srcPath+basename)
            else:
                shutil.copy2(parameters['GENERAL']['Path'], srcPath+basename)

        t_ref   = recording.StartTime
        t_end   = recording.StopTime
        t_min   = datetime.max
        t_max   = datetime.min
        t_ev_min= datetime.max
        t_ev_max= datetime.min

        if t_ref == datetime.min:
            Logger.warning("Unable to get StartTime of record. Will be set to first data point.")
        if t_end == datetime.min:
            Logger.warning("Unable to get EndTime of record. Will be set to last data point.")


        Logger.info("Reading channels")
        if eegform == "embla":
            channels = [EbmChannel(c) for c in glob.glob(parameters['GENERAL']['Path']+"*.ebm")]
            if parameters["DATATREATMENT"]['DropChannels'] != "":
                to_drop = [p.strip() for p in parameters['DATATREATMENT']['DropChannels'].split(',')]
                ch_dropped = [ch.GetId() for ch in channels if ch.GetName() in to_drop]
                channels = [ch for ch in channels if ch.GetName() not in to_drop]
            channels.sort()
            ch_dict = dict()
            
            for c in channels:
                Logger.debug("Channel {}, type {}, Sampling {} Hz".format(c.GetName(), c.GetId(), int(c.GetFrequency())))

                if c.GetId() in ch_dict:
                    Logger.warning("Channel {} has same Id {} as channel {}".format(c.GetName(), c.GetId(), ch_dict[c.GetId()].GetName() ))
                else:
                    ch_dict[c.GetId()] = c
                if t_ref != datetime.min:
                    if abs((t_ref - c.GetSequenceStart(0)).total_seconds()) > 60:
                        Logger.warning("Channel '{}': Starts {} sec later than recording".format(c.GetName(), (c.Time[0] - t_ref).total_seconds()))
                if c.Time[0] < t_min:
                    t_min = c.GetSequenceStart(0)
                    Logger.debug("New t_min {}".format(t_min.isoformat()))
                elif abs((c.GetSequenceStart(0) - t_min).total_seconds()) > 60:
                    Logger.warning("Channel '{}': Starts {} sec later than other channels".format(c.GetName(), (c.Time[0] - t_min).total_seconds()))
                if c.Time[-1]+timedelta(0, c._seqSize[-1]/c.GetFrequency(), 0) > t_max:
                    t_max = c.Time[-1]+timedelta(0, c._seqSize[-1]/c.GetFrequency(), 0) 
                    Logger.debug("New t_max {}".format(t_max.isoformat()))
                if int(c.GetFrequency()) != recording.Frequency:
                    Logger.debug("Channel '{}': Mismatch common sampling frequency {} Hz".format(c.GetName(), recording.Frequency))
                    fr = recording.Frequency
                    recording.AddFrequency(c.GetFrequency())
                    if fr != recording.Frequency:
                        Logger.info("Updated common sampling frequency to {} Hz".format(recording.Frequency))
                    
        else:
            raise Exception("EEG format {} not implemented (yet)".format(eegform))

        if t_ref == datetime.min:
            t_ref = t_min
        if t_end == datetime.min or t_end < t_max:
            t_end = t_max
            
        if entry_points[1] in plugins:
            result = plugins[entry_points[1]](channels, argv_plugin, parameters.items("PLUGINS"))
            if result != 0:
                raise Exception("Plugin {} returned code {}".format(entry_points[1], result))
       
        Logger.debug("Start time: {}, Stop time: {}".format(t_ref.isoformat(), t_end.isoformat()))
        Logger.debug("Earliest time: {}, Latest time: {}".format(t_min.isoformat(), t_max.isoformat()))
        Logger.info("Duration: {}".format(t_end - t_ref))
        if parameters['DATATREATMENT']['StartTime'] != '':
            t = datetime.strptime(parameters['DATATREATMENT']['StartTime'], "%Y-%m-%d %H:%M:%S")
            if t > t_ref : 
                Logger.info("Cropping start time by {}".format(t - t_ref))
                t_ref = t
        if parameters['DATATREATMENT']['EndTime'] != '':
            t = datetime.strptime(parameters['DATATREATMENT']['EndTime'], "%Y-%m-%d %H:%M:%S")
            if t < t_end : 
                Logger.info("Cropping end time by {}".format(t_end - t))
                t_end = t


        events = []
        Logger.info("Reading events info")
        if eegform == "embla":
            for evfile in glob.glob(parameters['GENERAL']['Path']+"*.esedb"):
                esedb = olefile.OleFileIO(evfile).openstream('Event Store/Events')
                root = Parcel(esedb)
                evs     = root.get("Events")
                aux_l   = root.getlist("Aux Data")[0]
                grp_l   = root.getlist("Event Types")[0].getlist()
                times   = root.getlist("EventsStartTimes")[0]
                locat   = root.get("Locations", 0)
                    
                for ev,time in zip(evs, times):
                    ev_id = -1
                    ch_id = locat.getlist("Location")[ev.LocationIdx].get("Signaltype").get("MainType")
                    ch_id += "_"+locat.getlist("Location")[ev.LocationIdx].get("Signaltype").get("SubType")
            
                    ch = None
                    if ch_id in ch_dict:
                        ch  = ch_dict[ch_id]
                    else:
                        if ch_id not in ch_dropped:
                            Logger.warning("Channel Id '{}' not in the list of channels".format(ch_id))
                        continue
                        
                    try:
                        name = grp_l[ev.GroupTypeIdx]
                    except:
                        try:
                            name = aux_l.get("Aux", ev.AuxDataID).get("Sub Classification History").get("1").get("type")
                        except:
                            Logger.warning("Can't get event name for index {}".format(ev.AuxDataID))
                            name = ""

                    if ch != None:
                        ch_index = channels.index(ch)
                    else:
                        ch_index = 0
                        continue
                    evnt = GenEvent(Name = name, Time = time, Duration = ev.TimeSpan)
                    evnt.AddChannel(ch_id)
                    if not evnt in events:
                        bisect.insort(events,evnt)
                    else :
                        events[events.index(evnt)].AddChannel(ch_id)

                    if parameters["DATATREATMENT"]["StartEvent"] == name and time > t_ref and time < t_ev_min:
                        t_ev_min = time
                        Logger.info("Cropping start time by {} from event {}".format(time - t_ref, name))
                    if parameters["DATATREATMENT"]["EndEvent"]   == name and time < t_end and time > t_ev_max:
                        t_ev_max = time
                        Logger.info("Cropping end time by {} from event {}".format(t_end - time, name))
                esedb.close()
        else:
            raise Exception("EEG format {} not implemented (yet)".format(eegform))

        ##Treating events
        if t_ev_min != datetime.max: t_ref = t_ev_min
        if t_ev_max != datetime.min: t_end = t_ev_max

        if parameters.getboolean("DATATREATMENT","IncludeSegmentStart"):
            for i, ch in enumerate(channels):
                for t in ch.Time:
                    ev = GenEvent(Name = "New Segment", Time = t, Duration = 0)
                    ev.AddChannel(ch.GetId())
                    if not ev in events:
                        bisect.insort(events,ev)
                    else :
                        events[events.index(ev)].AddChannel(ch.GetId())
        
        if parameters.getboolean("DATATREATMENT","IgnoreOutOfTimeEvents"):
            events = [ev for ev in events if (ev.GetTime() >= t_ref and ev.GetTime() <= t_end) ]

        if entry_points[2] in plugins:
            result = plugins[entry_points[2]](events, argv_plugin, parameters.items("PLUGINS"))
            if result != 0:
                raise Exception("Plugin {} returned code {}".format(entry_points[2], result))

        Logger.info("Creating eeg.json file")
        with open(recording.eegPath+"/"+recording.Prefix(app="_eeg.json"), "w") as f:
            recording.UpdateJSON()
            counter = {"EEGChannelCount":0, "EOGChannelCount":0, "ECGChannelCount":0, "EMGChannelCount":0, "MiscChannelCount":0}
            for ch in channels:
               if   "EEG" in ch.SigType: counter["EEGChannelCount"] += 1
               elif "EOG" in ch.SigType: counter["EOGChannelCount"] += 1
               elif "ECG" in ch.SigType or "EKG" in ch.SigType : counter["ECGChannelCount"] += 1
               elif "EMG" in ch.SigType: counter["EMGChannelCount"] += 1
               else: counter["MiscChannelCount"] += 1
            recording.JSONdata.update(counter)
            res = recording.CheckJSON()
            if len(res[0]) > 0:
                Logger.warning("JSON: Missing next required fields: "+ str(res[0]))
            if len(res[1]) > 0:
                Logger.info("JSON: Missing next recomennded fields: "+ str(res[1]))
            if len(res[2]) > 0:
                Logger.debug("JSON: Missing next optional fields: "+ str(res[2]))
            if len(res[3]) > 0:
                Logger.warning("JSON: Contains next non BIDS fields: "+ str(res[3]))
            json.dump(recording.JSONdata, f, skipkeys=False, indent="  ", separators=(',',':'))

        #Rounding t_ref to seconds
        t_ref = t_ref.replace(microsecond=0)
        #Updating channels frequency multiplier and starting time
        time_limits = list()
        for c in channels:
            c.SetFrequencyMultiplyer(int(recording.Frequency/c.GetFrequency()))
            c.SetStartTime(t_ref)
            if parameters.getboolean("RUNS","SplitRuns"):
                if c.GetName() == parameters["RUNS"]["MainChannel"]:
                    for i in range(0, c.GetNsequences()):
                        span = c.GetSequenceSize(i)/c.GetFrequency()
                        if (span/60) > float(parameters["RUNS"]["MinSpan"]):
                            ts = max(c.GetSequenceStart(i), t_ref).replace(microsecond=0)
                            te = min(c.GetSequenceStart(i) + timedelta(seconds=span), t_end)
                            if t_ref < te:
                                time_limits.append([ts, te])
        if len(time_limits) == 0:
            if parameters.getboolean("RUNS","SplitRuns"):
                raise Exception("Unable to find main channel '{}', needed to split into runs".format(parameters["RUNS"]["MainChannel"]))
            time_limits.append([t_ref, t_end])
        
        if entry_points[3] in plugins:
            result = plugins[entry_points[3]](time_limits, argv_plugin, parameters.items("PLUGINS"))
            if result != 0:
                raise Exception("Plugin {} returned code {}".format(entry_points[3], result))
    

        #Running over runs
        file_list = list()
        mem_requested = float(parameters["GENERAL"]["MemoryUsage"])*(1024**3)
        if parameters['GENERAL']['Conversion'] == "EDF":
            mem_1s = 32*sum(ch.GetFrequency() for ch in channels)
        elif parameters['GENERAL']['Conversion'] == "BV": 
            mem_1s = 32*len(channels)*recording.Frequency

        for count,t in enumerate(time_limits):
            t_ref = t[0]
            t_end = t[1]
            run = ""
            if parameters.getboolean("RUNS","SplitRuns"):
                run = str(count+1)
                Logger.info("Run {}: duration: {}".format(run, t_end - t_ref))
            
            Logger.info("Creating channels.tsv file")
            with open(recording.eegPath+recording.Prefix(run=run,app="_channels.tsv"), "w") as f:
                print("name", "type", "units", "description", "sampling_frequency", "reference", 
                    sep='\t', file = f)
                for c in channels:
                    print   (  
                            c.GetName(Void = "n/a"), c.GetType(Void = "n/a"), c.GetUnit(Void = "n/a"),
                            c.GetDescription(Void = "n/a"), c.GetFrequency(), 
                            c.GetReference(Void = "n/a"), sep = "\t", file = f
                            )

            Logger.info("Creating events.tsv file")     
            with open(recording.eegPath+recording.Prefix(run=run,app="_events.tsv"), "w") as f:
                print   (
                        "onset", "duration", "trial_type", 
                        "responce_time", "value", "sample", 
                        sep='\t', file = f
                        )
                for ev in events:
                    if ev.GetChannelsSize() == 0 or parameters.getboolean("DATATREATMENT","MergeCommonEvents"):
                        print   (  
                                "%.3f\t%.2f\t%s\tn/a\tn/a\t%d" %(
                                    ev.GetOffset(t_ref), ev.GetDuration(), 
                                    ev.GetName(Void = "n/a", ToReplace=("\t"," ")), 
                                    ev.GetOffset(t_ref)*recording.Frequency), 
                                file = f 
                                )
                    else :
                        for c_id in ev.GetChannels():
                            print(
                                    "%.3f\t%.2f\t%s\tn/a\tn/a" %(
                                        ev.GetOffset(t_ref), ev.GetDuration(), 
                                        ev.GetName(Void = "n/a", ToReplace=("\t"," "))), 
                                    file = f, end=""
                                )
                            #This writes index with channel proper frequency
                            #print("\t{}".format(channels[ev["Channel"]].GetIndexTime(ev["Time"], freqMultiplier = 1, StartTime=t_ref)), file = f)
                            #This writes index with common frequency
                            print("\t{}".format(ch_dict[c_id].GetIndexTime(ev.GetTime(),StartTime=t_ref)), file = f)

                                
            outData = None
            if  parameters['GENERAL']['Conversion'] == "BV":
                Logger.info("Converting to BrainVision format")
                outData = BrainVision(recording.eegPath, recording.Prefix(run=run), AnonymDate=ANONYM_DATE)
                outData.SetEncoding(parameters['BRAINVISION']['Encoding'])
                outData.SetDataFormat(parameters['BRAINVISION']['DataFormat'])
                outData.SetEndian(parameters['BRAINVISION']['Endian'] == "Little")
                outData.AddFrequency(recording.Frequency)

                Logger.info("Creating eeg.vhdr header file")
                for ch in channels:
                    outData.Header.Channels.append(BvChannel(Base = ch, Comments = ch.SigMainType+"-"+ch.SigSubType))
                outData.Header.write()
                
                Logger.info("Creating eeg.vmrk markers file")
                outData.MarkerFile.OpenFile(outData.GetEncoding())
                outData.MarkerFile.SetFrequency(outData.GetFrequency())
                outData.MarkerFile.SetStartTime(t_ref)
                Logger.info("Writting proper events")
                outData.MarkerFile.AddMarker("New Segment", t_ref, 0, -1, "")
                for ev in events:
                    if (ev.GetChannelsSize() == 0) or parameters.getboolean("DATATREATMENT","MergeCommonEvents"):
                        outData.MarkerFile.AddMarker(ev.GetName(ToReplace = (",","\1")), ev.GetTime(), ev.GetDuration(), -1, "")
                    else:
                        for c in ev.GetChannels():
                            outData.MarkerFile.AddMarker(ev.GetName(ToReplace = (",","\1")), ev.GetTime(), ev.GetDuration(), channels.index(ch_dict[c]), "")
                outData.MarkerFile.Write()

                Logger.info("Creating eeg data file")
                outData.DataFile.SetDataFormat(outData.Header.BinaryInfo.BinaryFormat)
                outData.DataFile.SetEndian(outData.Header.BinaryInfo.UseBigEndianOrder)
                outData.DataFile.OpenFile()
                t_e = t_ref
                t_count= 1

                mem_used = process.memory_info().rss
                mem_remained = mem_requested - mem_used
                t_step = int(mem_remained/mem_1s)
                Logger.debug("Memory used: {}, Memory requested: {}, Memory remined: {}".format(
                        humanbytes(mem_used), 
                        humanbytes(mem_requested),
                        humanbytes(mem_remained)))
                Logger.debug("1s time worth: {}".format(humanbytes(mem_1s)))
                Logger.debug("Time step:{}".format(timedelta(seconds=t_step)))
                while True:
                    t_s = t_e
                    t_e = t_e + timedelta(0,t_step,0)
                    if t_s >= t_end: break
                    if t_e > t_end: 
                        t_e = t_end
                        t_step = (t_e - t_s).total_seconds()
                    Logger.info("Timepoint {}: Duration {}".format(t_count,t_e -t_s))
                    Logger.debug("From {} to {} ({})sec.".format(t_s.isoformat(), t_e.isoformat(), (t_e - t_s).total_seconds()))
                    l_data = []
                    for ch in channels:
                        if outData.Header.BinaryInfo.BinaryFormat == "IEEE_FLOAT_32":
                            l_data.append(ch.GetValueVector(t_s, t_e, freq_mult=ch.GetFrequencyMultiplyer()))
                        else:
                            l_data.append(ch.GetValueVector(t_s, t_e, freq_mult=ch.GetFrequencyMultiplyer(), raw = True ))
                    
                    if entry_points[4] in plugins:
                        result = plugins[entry_points[4]](channels,l_data,argv_plugin, parameters.items("PLUGINS"))
                        if result != 0:
                            raise Exception("Plugin {} returned code {}".format(entry_points[4], result))
                    outData.DataFile.WriteBlock(l_data)
                    t_count += 1
                file_list.append("eeg/{}\t{}".format(
                        recording.Prefix(run=run,app="_eeg.vhdr"), 
                        t[0].isoformat()))

            #EDF part
            elif parameters['GENERAL']['Conversion'] == "EDF":
                Logger.info("Converting to EDF+ format")
                outData = EDF(recording.eegPath, recording.Prefix(run=run), AnonymDate=ANONYM_DATE)
                outData.Patient["Code"] = metadata["PatientInfo"]["ID"]
                if "Gender" in metadata["PatientInfo"]:
                    outData.Patient["Sex"] = "F" if metadata["PatientInfo"]["Gender"] == 1 else "M"
                if recording.SubjectInfo.Birth != datetime.min and ANONYM_BIRTH != "":
                    if ANONYM_BIRTH != None:
                        outData.Patient["Birthdate"] = ANONYM_BIRTH
                    else :
                        outData.Patient["Birthdate"] = metadata["PatientInfo"]["DateOfBirth"].date()

                outData.Patient["Name"] = recording.SubjectInfo.Name
                
                #outData.Record["StartDate"] = recording.StartTime
                outData.Record["StartDate"] = t_ref.replace(microsecond=0)
                outData.Record["Code"]      = metadata["RecordingInfo"]["Type"]
                outData.Record["Equipment"] = metadata["Device"]["DeviceID"]
                outData.SetStartTime(t_ref)
                outData.RecordDuration = int(parameters["EDF"]["DataRecordDuration"])

                Logger.info("Creating events.edf file")
                for ev in events:
                    if (ev.GetChannelsSize() == 0) or parameters.getboolean("DATATREATMENT","MergeCommonEvents"):
                        outData.AddEvent(ev.GetName(), ev.GetTime(), ev.GetDuration(), -1, "")
                    else:
                        for c in ev.GetChannels():
                            outData.AddEvent(ev.GetName(), ev.GetTime(), ev.GetDuration(), channels.index(ch_dict[c]), "")
                outData.WriteEvents()
                    
                Logger.info("Creating eeg.edf file")
                for ch in channels:
                    outData.Channels.append(EDFChannel(Base = ch, Type = ch.SigMainType, 
                        Specs = ch.SigMainType+"-"+ch.SigSubType, Filter = ""))
                outData.WriteHeader()
                t_e = t_ref

                mem_used = process.memory_info().rss
                mem_remained = mem_requested - mem_used
                t_step = int(mem_remained/mem_1s)
                Logger.debug("Memory used: {}, Memory requested: {}, Memory remined: {}".format(
                        humanbytes(mem_used), 
                        humanbytes(mem_requested),
                        humanbytes(mem_remained)))
                Logger.debug("Memory expected for 1s: {}".format(humanbytes(mem_1s)))
                Logger.debug("Time step:{}".format(timedelta(seconds=t_step)))
                if t_step%outData.RecordDuration != 0:
                    t_step = outData.RecordDuration*(t_step//outData.RecordDuration+1)
                t_count= 1
                while True:
                    t_s = t_e
                    t_e = t_e + timedelta(0,t_step,0)
                    if t_s >= t_end: break
                    if t_e > t_end: 
                        t_e = t_end
                        t_step = (t_e - t_s).total_seconds()
                        if t_step%outData.RecordDuration != 0:
                            t_step = outData.RecordDuration*(t_step//outData.RecordDuration+1)
                            t_e = t_s + timedelta(0,t_step,0)

                    Logger.info("Timepoint {}: Duration {}".format(t_count,t_e -t_s))
                    Logger.debug("From {} to {} ({})sec.".format(t_s.isoformat(), t_e.isoformat(), (t_e - t_s).total_seconds()))
                    l_data = []
                    for ch in channels:
                        l_data.append(ch.GetValueVector(t_s, t_e, freq_mult=1, raw = True ))
                    
                    if entry_points[4] in plugins:
                        result = plugins[entry_points[4]](channels,l_data,argv_plugin, parameters.items("PLUGINS"))
                        if result != 0:
                            raise Exception("Plugin {} returned code {}".format(entry_points[4], result))
                    outData.WriteDataBlock(l_data, t_s)
                    t_count += 1
                outData.Close()

                file_list.append("eeg/{}\t{}".format(
                        recording.Prefix(run=run,app="_eeg.edf"), 
                        t[0].isoformat()))

            with open(parameters['GENERAL']['OutputFolder']+recording.Path(app="scans.tsv"), "a") as f:
                for l in file_list:
                    print(l, file = f)

        #Copiyng original files if there no conversion
        if parameters['GENERAL']["Conversion"] == "":
            Logger.info("Copying original files")
            for f in recording.GetMainFiles(path=parameters['GENERAL']['Path']):
                Logger.debug("file: "+f)
                shutil.copy2(
                        parameters['GENERAL']['Path']+f, 
                        recording.eegPath+recording.Prefix(app="_"+f)
                        )

        #Copiyng auxiliary files
        Logger.info("Copying auxiliary files")
        for f in recording.GetAuxFiles(path=parameters['GENERAL']['Path']):
            Logger.debug("file: "+f)
            shutil.copy2(
                        parameters['GENERAL']['Path']+f, 
                        recording.eegPath+recording.Prefix(app="_"+f)
                        )

        with open(parameters['GENERAL']['OutputFolder']+"participants.tsv", "a") as f:
            s_id = recording.SubjectInfo.ID
            s_gen = "n/a"
            if recording.SubjectInfo.Gender == 1: 
                s_gen = "F"
            elif recording.SubjectInfo.Gender == 2:
                s_gen = "M"
            s_age = "n/a"
            if recording.SubjectInfo.Birth != datetime.min:
                s_age = str(time_limits[0][0].year - recording.SubjectInfo.Birth.year)
            print("{}\t{}\t{}".format(s_id, s_gen, s_age), file = f)


    except Exception as e:
        exc_type, exc_value, exc_traceback = os.sys.exc_info()
        tr = traceback.extract_tb(exc_traceback)
        for l in tr:
            Logger.error('File "'+l[0]+'", line '+str(l[1])+" in "+l[2]+":")
        Logger.error(type(e).__name__+": "+str(e))
        if recording != None and recording.eegPath != None:
            flist = glob.glob(recording.eegPath+recording.Prefix(app="*"))
            if len(flist) != 0:
                for f in flist:
                    rmdir(f)
        Logger.info("Command: "+" ".join(argv))

        ex_code = 1

    try:
        Logger.info(">>>>>>>>>>>>>>>>>>>>>>")
        Logger.info("Took {} seconds".format(tm.process_time()))
        Logger.info("<<<<<<<<<<<<<<<<<<<<<<")
        shutil.copy2(tmpDir+"/logfile", recording.eegPath+recording.Prefix(app=".log"))
        shutil.copy2(tmpDir+"/configuration", recording.eegPath+recording.Prefix(app=".ini")) 
        fileHandler.close()
        rmdir(tmpDir)
        shutil.rmtree(tmpDir)
    except Exception as e:
        Logger.error("Unable to copy files to working directory. See in "+tmpDir+"logfile for more details.")
        exc_type, exc_value, exc_traceback = os.sys.exc_info()
        tr = traceback.extract_tb(exc_traceback)
        for l in tr:
            Logger.error('File "'+l[0]+'", line '+str(l[1])+" in "+l[2]+":")
        Logger.error(type(e).__name__+": "+str(e))
        ex_code = 1

    return(ex_code)

if __name__ == "__main__":
    os.sys.exit(main(os.sys.argv))
