VERSION = '0.5'

import logging, argparse, os, json, glob, olefile, traceback, struct, configparser
import tempfile
from datetime import datetime, timedelta
import time as tm

from DataStructure.Generic.Record import Record as GRecord

from DataStructure.Embla.Record  import ParceRecording
from DataStructure.Embla.Channel import EbmChannel

from DataStructure.BrainVision.BrainVision import BrainVision

from DataStructure.EDF.EDF import EDF
from DataStructure.EDF.EDF import Channel as EDFChannel

import shutil

ex_code = 0


def rmdir(path):
    for root, dirs, files in os.walk(path):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))


parser = argparse.ArgumentParser(description='Converts EEG file formats to BID standard')

parser.add_argument('infile', 
    metavar='eegfile', nargs = 1,
    help='input eeg file')
parser.add_argument('-t, --task',
    metavar='taskId', dest='task',
    help = 'Id of the task' )
parser.add_argument('-a, --acquisition',
    metavar='acqId', dest='acq', 
    help = 'Id of the acquisition' )
parser.add_argument('-s, --session',
    metavar='sesId', dest='ses',
    help = 'Id of the session' )
parser.add_argument('-r, --run,',
    metavar='runId', dest='run',
    help = 'Id of the run' )
parser.add_argument('-j, --json', 
    metavar='eegJson', dest='eegJson',
    help = "A json file with task description"
    )
parser.add_argument('-o, --output', nargs=1, dest='outdir',
    help='destination folder')


parser.add_argument('-c, --config', nargs='?', dest='config_file',
    help="Path to configuration file")

parser.add_argument('--logfile', nargs='?',
    metavar='log.out', dest='logfile',
    help='log file destination')

parser.add_argument('-q,--quiet', dest='quiet', action="store_true", help="Supress standard output")
parser.add_argument('--log', dest='loglevel', choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    help='logging level')
parser.add_argument('--version', action='version', version='%(prog)s '+VERSION)


subparsers = parser.add_subparsers(title='conversions', help='do <command --help> for additional help', dest="command")
group_bv = subparsers.add_parser('BrainVision', help='Conversion to BrainVision format')
group_bv.add_argument('--encoding', dest='bv_encoding', choices=["UTF-8","ANSI"],
    help='Header encoding')
group_bv.add_argument('--format', dest='bv_format', choices=['IEEE_FLOAT_32', 'INT_16', 'UINT_16'], help='Data number format')
group_bv.add_argument('--big_endian', dest='bv_endian', action="store_true", help='Use big endian')


group_edf = subparsers.add_parser('EDF', help='Conversion to EDF format')

args = parser.parse_args()

parameters = configparser.ConfigParser()
#Making keys case-sensitive
parameters.optionxform = lambda option: option

#Setting up default values
parameters['GENERAL'] = {"TaskId":"", "AcquisitionId":"", "SessionId":"", "RunId":"",
                        "JsonFile":"",
                        "OutputFolder":".", 
                        "LogLevel":"INFO", 
                        "Quiet":"no",
                        "Conversion":""}
parameters['DATATREATMENT'] = {"DropChannels":"", "StartTime":"", "EndTime":"", 
                                "StartEvent":"","EndEvent":"",
                                "IgnoreOutOfTimeEvents":"yes",
                                "MergeCommonEvents":"yes",
                                "IncludeSegmentStart":"yes"}
parameters['BRAINVISION']   = {"Encoding":"UTF-8", "DataFormat":"IEEE_FLOAT_32", "Endian":"Little"}

#Reading configuration file
if args.config_file != None:
    parameters.read(args.config_file)

#Overloading values by command-line arguments
if args.task != None : parameters['GENERAL']['TaskId']          = args.task
if args.acq  != None : parameters['GENERAL']['AcquisitionId']   = args.acq
if args.ses  != None : parameters['GENERAL']['SessionId']       = args.ses
if args.run  != None : parameters['GENERAL']['RunId']           = args.run
if args.eegJson  != None: parameters['GENERAL']['JsonFile']     = args.eegJson
if args.loglevel != None: parameters['GENERAL']['LogLevel']     = args.loglevel
if args.quiet == True : parameters['GENERAL']['Quiet']          = 'yes'
if args.command != None : parameters['GENERAL']['Conversion']   = args.command
if args.infile  != None : parameters['GENERAL']['Path']         = os.path.realpath(args.infile[0])
if args.outdir  !=None  : parameters['GENERAL']['OutputFolder'] = os.path.realpath(args.outdir[0])

if parameters['GENERAL']['Conversion']      == "BrainVision":
    if hasattr(args, 'bv_encoding') and args.bv_encoding != None : parameters['BRAINVISION']['Encoding']   = args.bv_encoding
    if hasattr(args, 'bv_format') and args.bv_format   != None : parameters['BRAINVISION']['DataFormat'] = args.bv_format
    if hasattr(args,'bv_endian'):
        parameters['BRAINVISION']['Endian']     = ("Little" if args.bv_endian else "Big")
    
eegform = None

'''
Setup logging.
Logfile will be stored into temporary directory first, then moved to output directory.
'''
tmpDir = tempfile.mkdtemp(prefix=os.sys.argv[0]+"_")

#logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s", datefmt='%m/%d/%Y %H:%M:%S')
logFormatter = logging.Formatter("%(levelname)s:%(asctime)s: %(message)s", datefmt='%m/%d/%Y %H:%M:%S')
Logger = logging.getLogger()
Logger.setLevel(getattr(logging, parameters['GENERAL']['LogLevel'], None))

fileHandler = logging.FileHandler(tmpDir+"/logfile")
fileHandler.setFormatter(logFormatter)
Logger.addHandler(fileHandler)

if not parameters['GENERAL'].getboolean('Quiet'):
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    Logger.addHandler(consoleHandler)




Logger.debug(str(os.sys.argv))
Logger.debug("Temporary directory: "+tmpDir)
with open(tmpDir+"/configuration", 'w') as configfile: parameters.write(configfile)



Logger.info("Task: {}".format(parameters['GENERAL']['TaskId']))
if parameters['GENERAL']['AcquisitionId'] != '' :
    Logger.info("Acquisition: {}".format(parameters['GENERAL']['AcquisitionId']))
Logger.info("File: {}".format(parameters['GENERAL']['Path']))
try:
    dirName = ""
    if not os.path.exists(parameters['GENERAL']['Path']):
        raise Exception("Path {} is not valid".format(parameters['GENERAL']['Path']))       
    if os.path.isdir(parameters['GENERAL']['Path']):
        dirName = os.path.basename(parameters['GENERAL']['Path'])
        if len(glob.glob(parameters['GENERAL']['Path']+'/*.ebm')) > 0:
            eegform = "embla"
    elif os.path.splitext(parameters['GENERAL']['Path'])[0] == '.edf':
        eegform = "edf"
    else:
        raise Exception("Unable determine eeg format")
    
    JSONdata = dict()
    if parameters['GENERAL']['JsonFile'] != "":
        parameters['GENERAL']['JsonFile'] = os.path.realpath(parameters['GENERAL']['JsonFile'])
        Logger.info("JSON File: {}".format(parameters['GENERAL']['JsonFile']))
        if not os.path.isfile(parameters['GENERAL']['JsonFile']):
            raise Exception("File {} don't exists".format(parameters['GENERAL']['JsonFile']))
        with open(parameters['GENERAL']['JsonFile']) as f:
             JSONdata = json.load(f)
        t = JSONdata["TaskName"]
        if t != parameters['GENERAL']['TaskId']:
            t = ''.join(filter(str.isalnum, t))
            if parameters['GENERAL']['TaskId'] == "":
                parameters['GENERAL']['TaskId'] = t
            elif t != parameters['GENERAL']['TaskId']:
                raise Exception("Task name in JSON '{}' mismach given Task name '{}'".format(t, parameters['GENERAL']['TaskId']))

    Logger.info("Output: {}".format(parameters['GENERAL']['OutputFolder']))
    if not os.path.isdir(parameters['GENERAL']['Path']):
        raise Exception("Path {} is not valid".format(parameters['GENERAL']['Path']))

    recording = GRecord(task = parameters['GENERAL']['TaskId'], 
                        session = parameters['GENERAL']['SessionId'], 
                        acquisition = parameters['GENERAL']['AcquisitionId'],
                        run = parameters['GENERAL']['RunId'])
    eegPath = "/"
    srcPath = "/"
    if parameters['GENERAL']['JsonFile'] != "":
        with open(parameters['GENERAL']['JsonFile']) as f:
            recording.JSONdata = JSONdata
        if "SamplingFrequency" in recording.JSONdata:
            recording.Frequency = recording.JSONdata["SamplingFrequency"]
    
    if eegform == "embla":
        Logger.info("Detected {} format".format(eegform))
        if len(glob.glob(parameters['GENERAL']['Path']+'/Recording.esrc')) != 1 or len (glob.glob(parameters['GENERAL']['Path']+'/*.esedb')) != 1:
            raise Exception("Embla folder should contain exacly 1 Recording.escr and 1 events .esedb files")
        #Reading metadata
        esrc = olefile.OleFileIO(parameters['GENERAL']['Path']+'/Recording.esrc').openstream('RecordingXML')
        xml  = esrc.read().decode("utf_16_le")[2:-1]
        metadata = ParceRecording(xml)
        name = ""
        if metadata["PatientInfo"]["FirstName"] != None:
            name += metadata["PatientInfo"]["FirstName"]
        if metadata["PatientInfo"]["MiddleName"]!= None:
            name += " "+metadata["PatientInfo"]["MiddleName"]
        if metadata["PatientInfo"]["LastName"]  != None:
            name += " "+metadata["PatientInfo"]["LastName"]
        name = name.strip()
        birth = datetime.min
        if "DateOfBirth" in metadata["PatientInfo"]:
            birth = metadata["PatientInfo"]["DateOfBirth"]
        recording.StartTime = metadata["RecordingInfo"]["StartTime"]
        recording.StopTime  = metadata["RecordingInfo"]["StopTime"]
        recording.SetSubject (id = metadata["PatientInfo"]["ID"],
                            name  = name,
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
        Logger.info("Patient Id: {}".format(recording.SubjectInfo.ID))
        
    else:
        raise Exception("EEG format {} not implemented (yet)".format(eegform))
    
    recording.ResetPrefix()
    recording.ResetPath()
    eegPath = parameters['GENERAL']['OutputFolder']+"/"+ recording.Path()
    srcPath = parameters['GENERAL']['OutputFolder']+"/source/"+ recording.Path()
    Logger.info("Creating output directory {}".format(eegPath))
    try:
        os.makedirs(eegPath)
    except OSError:
        Logger.warning("Directory already exists. Contents will be erased.")
        rmdir(eegPath)
        
    Logger.info("Creating output directory {}".format(srcPath))
    try:
        os.makedirs(srcPath)
    except OSError:
        Logger.warning("Directory already exists. Contents will be erased.")
        rmdir(srcPath)
    
    Logger.info("Copiyng data to folders")
    if dirName != "":
        shutil.copytree(parameters['GENERAL']['Path'], srcPath+"/"+dirName)
    else:
        shutil.copy2(parameters['GENERAL']['Path'], srcPath)
    with open(eegPath+"/"+recording.Prefix()+".conf", 'w') as configfile: parameters.write(configfile)

    t_ref   = recording.StartTime
    t_end   = recording.StopTime
    t_min   = datetime.max
    t_max   = datetime.min
    t_ev_min= datetime.max
    t_ev_max= datetime.min

    Logger.info("Creating channels.tsv file")
    with open(eegPath+"/"+recording.Prefix()+"_channels.tsv", "w") as f:
        if eegform == "embla":
            channels = [EbmChannel(c) for c in glob.glob(parameters['GENERAL']['Path']+"/*.ebm")]
            print("name", "type", "units", "description", "sampling_frequency", "reference", 
                "low_cutoff", "high_cutoff", "notch", "status", "status_description", sep='\t', file = f)
            if parameters["DATATREATMENT"]['DropChannels'] != "":
                to_drop = [p.strip() for p in parameters['DATATREATMENT']['DropChannels'].split(',')]
                channels = [ch for ch in channels if ch.ChannName not in to_drop]
            channels.sort()
            ch_dict = dict()
            
            for c in channels:
                Logger.debug("Channel {}, type {}, Sampling {} Hz".format(c.ChannName, c.SigType, int(c.DBLsampling)))

                if c.SigSubType in ch_dict:
                    Logger.warning("Channel {} has same sub-type {} as channel {}".format(c.ChannName, c.SigSubType, ch_dict[c.SigSubType].ChannName ))
                else:
                    ch_dict[c.SigSubType] = c
                l = [c.ChannName, c.SigType, c.CalUnit, c.Header, int(c.DBLsampling), c.SigRef, "", "", "", "", ""]
                for field in l:
                    if type(field) is list:
                        field = str.join(" ", field)
                    if field == "":
                        field = "n/a"
                    print(field, end = '\t', file=f)
                print("", file = f)
                if t_ref != None:
                    if t_ref != c.Time[0]:
                        Logger.warning("Channel '{}': Starts {} sec later than recording {}".format(c.ChannName, (c.Time[0] - t_ref).total_seconds(), t_ref.isoformat()))
                if c.Time[0] < t_min:
                    t_min = c.Time[0]
                    Logger.debug("New t_min {}".format(t_min.isoformat()))
                elif c.Time[0] != t_min:
                    Logger.warning("Channel '{}': Starts {} sec later than other channels".format(c.ChannName, (c.Time[0] - t_min).total_seconds()))
                if c.Time[-1]+timedelta(0, c._seqSize[-1]*c.DBLsampling, 0) > t_max:
                    t_max = c.Time[-1]+timedelta(0, c._seqSize[-1]/c.DBLsampling, 0) 
                    Logger.debug("New t_max {}".format(t_max.isoformat()))
                if int(c.DBLsampling) != recording.Frequency:
                    Logger.debug("Channel '{}': Mismatch common sampling frequency {} Hz".format(c.ChannName, recording.Frequency))
                    fr = recording.Frequency
                    recording.AddFrequency(int(c.DBLsampling))
                    if fr != recording.Frequency:
                        Logger.info("Updated common sampling frequency to {} Hz".format(recording.Frequency))
                    
        else:
            raise Exception("EEG format {} not implemented (yet)".format(eegform))

    if t_ref == datetime.min:
        t_ref = t_min
    if t_end == datetime.min or t_end < t_max:
        t_end = t_max
    Logger.info("Start time: {}, Stop time: {}".format(t_ref.isoformat(), t_end.isoformat()))
    Logger.info("Earliest time: {}, Latest time: {}".format(t_min.isoformat(), t_max.isoformat()))
    if parameters['DATATREATMENT']['StartTime'] != '':
        t = datetime.strptime(parameters['DATATREATMENT']['StartTime'], "%Y-%m-%d %H:%M:%S.%f")
        if t > t_ref : 
            Logger.info("Cropping start time: from {} to {}".format(t_ref.isoformat(), t.isoformat()))
            t_ref = t
    if parameters['DATATREATMENT']['EndTime'] != '':
        t = datetime.strptime(parameters['DATATREATMENT']['EndTime'], "%Y-%m-%d %H:%M:%S.%f")
        if t < t_end : 
            Logger.info("Cropping end time: from {} to {}".format(t_end.isoformat(), t.isoformat()))
            t_end = t


    events = []
    Logger.info("Reading events info")
    if eegform == "embla":
        from  Parcel.parcel import Parcel
        evfile = glob.glob(parameters['GENERAL']['Path']+"/*.esedb")[0]
        esedb = olefile.OleFileIO(evfile).openstream('Event Store/Events')
        root = Parcel(esedb)
        evs     = root.get("Events")
        aux_l   = root.getlist("Aux Data")[0]
        grp_l   = root.getlist("Event Groups")[0]
        times   = root.getlist("EventsStartTimes")[0]
        locat   = root.get("Locations", 0)
            
        for ev,time in zip(evs, times):
            Logger.debug("Event {}, at {}, loc. {}, aux. {} ".format(ev.EventID, time.strftime("%d/%m/%Y %H:%M:%S.%f"), ev.LocationIdx, ev.AuxDataID))
            try :
                loc = locat.getlist("Location")[ev.LocationIdx].get("Signaltype").get("SubType") 
                ch  = ch_dict[loc]
                dt = (time - ch.Time[0]).total_seconds()
            except:
                Logger.warning("Channel '{}' not in the list of channels".format(loc))
                ch = None
                dt = float(ev.LocationIdx) 

            dt = (time - t_ref).total_seconds()

            try:
                aux = aux_l.get("Aux", ev.AuxDataID).get("Sub Classification History").get("1")
                name = aux.get("type")
            except:
                Logger.warning("Can't get event name for index {}".format(ev.AuxDataID))
                aux = None
                name = "n/a"

            if ch != None:
                ch_id = channels.index(ch)
            else:
                ch_id = 0
                continue
            events.append({"Name": name,  "Time":time, "Channel": ch_id, "Span": ev.TimeSpan, "Location": loc})

            if parameters["DATATREATMENT"]["StartEvent"] == name and time > t_ref and time < t_ev_min:
                t_ev_min = time
                Logger.info("Updated start time {} from event {}".format(time, name))
            if parameters["DATATREATMENT"]["EndEvent"]   == name and time < t_end and time > t_ev_max:
                t_ev_max = time
                Logger.info("Updated end time {} from event {}".format(time, name))
            
    else:
        raise Exception("EEG format {} not implemented (yet)".format(eegform))

    ##Treating events
    if t_ev_min != datetime.max: t_ref = t_ev_min
    if t_ev_max != datetime.min: t_end = t_ev_max

    if parameters.getboolean("DATATREATMENT","IncludeSegmentStart"):
        for i, ch in enumerate(channels):
            for t in ch.Time:
                events.append({"Name": "New Segment", "Time":t, "Channel": i, "Span":0., "Location":""})
    events.sort(key=lambda a: a["Time"])
    events.insert(0,{"Name": "New Segment", "Time":t_ref, "Channel": -1, "Span":0., "Location":""})
    if parameters.getboolean("DATATREATMENT","IgnoreOutOfTimeEvents"):
        events = [ev for ev in events if (ev["Time"] >= t_ref and ev["Time"] <= t_end) ]

    Logger.info("Creating events.tsv file")     
    with open(eegPath+"/"+recording.Prefix()+"_events.tsv", "w") as f:
        print("onset", "duration", "trial_type", "responce_time", "value", "sample", sep='\t', file = f)
        for ev in events:
            dt = (ev["Time"] - t_ref).total_seconds()
            print("%.3f\t%.2f\t%s\tn/a\tn/a"% (dt, ev["Span"], ev["Name"]), file = f, end="")
            if ev["Channel"] >= 0 :
                print("\t%d"%int(dt*channels[ev["Channel"]].DBLsampling), file = f )
            else : 
                print("\tn/a", file = f )
            
    logging.info("Creating eeg.json file")
    with open(eegPath+"/"+recording.Prefix()+"_eeg.json", "w") as f:
        recording.UpdateJSON()
        counter = {"EEGChannelCount":0, "EOGChannelCount":0, "ECGChannelCount":0, "EMGChannelCount":0, "MiscChannelCount":0}
        for ch in channels:
           if   ch.SigType == "EEG": counter["EEGChannelCount"] += 1
           elif ch.SigType == "EOG": counter["EOGChannelCount"] += 1
           elif ch.SigType == "ECG": counter["ECGChannelCount"] += 1
           elif ch.SigType == "EMG": counter["EMGChannelCount"] += 1
           else: counter["MiscChannelCount"] += 1
        recording.JSONdata.update(counter)
        res = recording.CheckJSON()
        if len(res[0]) > 0:
            logging.warning("JSON: Missing next required fields: "+ str(res[0]))
        if len(res[1]) > 0:
            logging.info("JSON: Missing next recomennded fields: "+ str(res[1]))
        if len(res[2]) > 0:
            logging.debug("JSON: Missing next optional fields: "+ str(res[2]))
        if len(res[3]) > 0:
            logging.warning("JSON: Contains next non BIDS fields: "+ str(res[3]))
        json.dump(recording.JSONdata, f, skipkeys=False, indent="  ", separators=(',',':'))

    outData = None
    if  parameters['GENERAL']['Conversion'] == "BrainVision":
        Logger.info("Converting to BrainVision format")
        outData = BrainVision(eegPath, recording.Prefix())
        outData.SetEncoding(parameters['BRAINVISION']['Encoding'])
        outData.SetDataFormat(parameters['BRAINVISION']['DataFormat'])
        outData.SetEndian(parameters['BRAINVISION']['Endian'] == "Little")
        outData.AddFrequency(recording.Frequency)

        Logger.info("Creating eeg.vhdr header file")
        for ch in channels:
            outData.AddChannel(ch.ChannName, '', ch.Scale(), ch.Unit(), "{} at {}".format(ch.SigMainType, ch.SigSubType ))
        outData.Header.write()
        
        Logger.info("Creating eeg.vmrk markers file")
        outData.MarkerFile.OpenFile(outData.GetEncoding())
        outData.MarkerFile.SetFrequency(outData.GetFrequency())
        outData.MarkerFile.SetStartTime(t_ref)
        Logger.info("Writting proper events")
        for ev in events:
            outData.MarkerFile.AddMarker(ev["Name"], ev["Time"], ev["Span"], ev["Channel"], "")
        outData.MarkerFile.Write()

        Logger.info("Creating eeg data file")
        outData.DataFile.SetDataFormat(outData.Header.BinaryInfo.BinaryFormat)
        outData.DataFile.SetEndian(outData.Header.BinaryInfo.UseBigEndianOrder)
        outData.DataFile.OpenFile()
        t_e = t_ref
        while True:
            t_s = t_e
            t_e = t_e + timedelta(0,3600,0)
            if t_s >= t_end: break
            if t_e > t_end: t_e = t_end
            Logger.info("Timepoint: {}".format(t_s.isoformat()))
            Logger.debug("From {} to {} ({})sec.".format(t_s.isoformat(), t_e.isoformat(), (t_e - t_s).total_seconds()))
            l_data = []
            for ch in channels:
                if outData.Header.BinaryInfo.BinaryFormat == "IEEE_FLOAT_32":
                    l_data.append(ch.getValueVector(t_s, t_e, freq_mult=int(outData.GetFrequency()/ch.DBLsampling)))
                else:
                    l_data.append(ch.getValueVector(t_s, t_e, freq_mult=int(outData.GetFrequency()/ch.DBLsampling), raw = True ))
            outData.DataFile.WriteBlock(l_data)
    elif parameters['GENERAL']['Conversion'] == "EDF":
        Logger.info("Converting to EDF+ format")
        Logger.info("Creating events.edf file")
        outData = EDF(eegPath, recording.Prefix())
        Logger.info("Creating events.edf file")
        outData.Patient["Code"] = metadata["PatientInfo"]["ID"]
        if "Gender" in metadata["PatientInfo"]:
            outData.Patient["Sex"] = "F" if metadata["PatientInfo"]["Gender"] == 1 else "M"
        if "DateOfBirth" in metadata["PatientInfo"]:
            outData.Patient["Birthdate"] = metadata["PatientInfo"]["DateOfBirth"].date()

        name = ""
        if "FirstName" in metadata["PatientInfo"] and metadata["PatientInfo"]["FirstName"] != None:
            name += metadata["PatientInfo"]["FirstName"]+" "
        if "MiddleName" in metadata["PatientInfo"] and metadata["PatientInfo"]["MiddleName"] != None:
            name += metadata["PatientInfo"]["MiddleName"]+" "
        if "LastName" in metadata["PatientInfo"] and metadata["PatientInfo"]["LastName"] != None:
            name += metadata["PatientInfo"]["LastName"]+" "
        outData.Patient["Name"] = name.strip()
        
        outData.Record["StartDate"] = metadata["RecordingInfo"]["StartTime"] 
        outData.Record["Code"]  = metadata["RecordingInfo"]["Type"]
        outData.Record["Equipment"] = metadata["Device"]["DeviceID"]
        outData.SetStartTime(t_ref)
        outData.RecordDuration = 10.

        for ev in events:
            outData.AddEvent(ev["Name"], ev["Time"], ev["Span"], ev["Channel"], "")
        outData.WriteEvents()
            
        for ch in channels:
            outData.Channels.append(EDFChannel(Base = ch, Type = ch.SigMainType, 
                Specs = ch.SigMainType+"-"+ch.SigSubType, Filter = ""))
        outData.WriteHeader()
        t_e = t_ref
        t_step = 3600
        if t_step%outData.RecordDuration != 0:
            t_step = outData.RecordDuration*(t_step//outData.RecordDuration+1)
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

            Logger.info("Timepoint: {}".format(t_s.isoformat()))
            Logger.debug("From {} to {} ({})sec.".format(t_s.isoformat(), t_e.isoformat(), (t_e - t_s).total_seconds()))
            l_data = []
            for ch in channels:
                l_data.append(ch.GetValueVector(t_s, t_e, raw = True ))
            outData.WriteDataBlock(l_data, t_s)
        outData.Close()

        

    Logger.info("All done. Took {} secons".format(tm.process_time()))

except Exception as e:
    Logger.error(e)
    traceback.print_exc()
    Logger.info("Took {} seconds".format(tm.process_time()))

    ex_code = 1

try:
    shutil.copy2(tmpDir+"/logfile", eegPath+"/"+recording.Prefix()+".log") 
    shutil.copy2(tmpDir+"/configuration", eegPath+"/"+recording.Prefix()+".conf") 
    rmdir(tmpDir)
    shutil.rmtree(tmpDir)
except:
    Logger.error("Unable to copy files to working directory. See in "+tmpDir+"/logfile for more details.")
    ex_code = 1

exit(ex_code)
