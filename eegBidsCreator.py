VERSION = '0.5'

import logging, argparse, os, json, glob, olefile, traceback, struct
from datetime import datetime, timedelta
import time as tm

from DataStructure.Record import ParceRecording
from DataStructure.BrainVision.BrainVision import BrainVision

import shutil

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
    metavar='acqId', dest='acq', default='',
    help = 'Id of the acquisition' )
parser.add_argument('-s, --session',
    metavar='sesId', dest='ses', default='',
    help = 'Id of the session' )
parser.add_argument('-r, --run,',
    metavar='runId', dest='run', default='',
    help = 'Id of the run' )
parser.add_argument('-j, --json', nargs=1, default='',
    metavar='eegJson', dest='eegJson',
    help = "A json file with task description"
    )
parser.add_argument('-o, --output', nargs=1, default='.', dest='outdir',
    help='destination folder')
parser.add_argument('--logfile', nargs='?', default='',
    metavar='log.out', dest='logfile',
    help='log file destination')

parser.add_argument('--log', dest='loglevel', default='INFO', choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    help='logging level')
parser.add_argument('--version', action='version', version='%(prog)s '+VERSION)


subparsers = parser.add_subparsers(title='conversions', help='do <command --help> for additional help', dest="command")
group_bv = subparsers.add_parser('BrainVision', help='Conversion to BrainVision format')
group_bv.add_argument('--encoding', dest='bv_encoding', default='UTF-8', choices=["UTF-8","ANSI"],
    help='Header encoding')
group_bv.add_argument('--format', dest='bv_format', default='IEEE_FLOAT_32', choices=['IEEE_FLOAT_32', 'INT_16', 'UINT_16'], help='Data number format')
group_bv.add_argument('--big_endian', dest='bv_endian', action="store_true", help='Use big endian')



args = parser.parse_args()
print(args)

numeric_level = getattr(logging, args.loglevel, None)
logging.basicConfig(filename=args.logfile, filemode='w', level=numeric_level,
    format='%(levelname)s:%(asctime)s: %(message)s', datefmt='%m/%d/%Y %H:%M:%S')

task    = args.task
acq     = args.acq
ses     = args.ses
run     = args.run
eegJson = args.eegJson
path    = os.path.realpath(args.infile[0])
eegform = None
outdir  = os.path.realpath(args.outdir[0])

logging.info("Task: {}".format(task))
if acq != '' :
    logging.info("Acquisition: {}".format(acq))
logging.info("File: {}".format(path))
try:
    dirName = ""
    if not os.path.exists(path):
        raise Exception("Path {} is not valid".format(path))       
    if os.path.isdir(path):
        dirName = os.path.basename(path)
        if len(glob.glob(path+'/*.ebm')) > 0:
            eegform = "embla"
    elif os.path.splitext(path)[0] == '.edf':
        eegform = "edf"
    else:
        raise Exception("Unable determine eeg format")
    
    if len(eegJson) == 1:
        eegJson = os.path.realpath(eegJson[0])
        logging.info("JSON File: {}".format(eegJson))
        if not os.path.isfile(eegJson):
            raise Exception("File {} don't exists".format(eegJson))
        f = open(eegJson)
        eegJson = json.load(f.read())
        f.close()

    logging.info("Output: {}".format(outdir))
    if not os.path.isdir(path):
        raise Exception("Path {} is not valid".format(path))
    metadata = dict()
    
    if eegform == "embla":
        logging.info("Detected {} format".format(eegform))
        if len(glob.glob(path+'/Recording.esrc')) != 1 or len (glob.glob(path+'/*.esedb')) != 1:
            raise Exception("Embla folder should contain exacly 1 Recording.escr and 1 events .esedb files")
        #Reading metadata
        esrc = olefile.OleFileIO(path+'/Recording.esrc').openstream('RecordingXML')
        xml  = esrc.read().decode("utf_16_le")[2:-1]
        metadata = ParceRecording(xml)
        esrc.close()
        logging.info("Patient Id: {}".format(metadata["PatientInfo"]["ID"]))
        
    else:
        raise Exception("EEG format {} not implemented (yet)".format(eegform))


    
    eegPath = outdir+"/sub-"+metadata["PatientInfo"]["ID"]
    srcPath = outdir+"/source/sub-"+metadata["PatientInfo"]["ID"]
    if ses != '':
        eegPath = eegPath+"/ses-"+ses+"/eeg"
        srcPath = srcPath+"/ses-"+ses+"/eeg"
    else:
        eegPath = eegPath+"/eeg"
        srcPath = srcPath+"/eeg"
    logging.info("Creating output directory {}".format(eegPath))
    try:
        os.makedirs(eegPath)
    except OSError:
        logging.warning("Directory already exists. Contents will be eraised.")
        rmdir(eegPath)
        
    logging.info("Creating output directory {}".format(srcPath))
    try:
        os.makedirs(srcPath)
    except OSError:
        logging.warning("Directory already exists. Contents will be erased.")
        rmdir(srcPath)
    prefix = "sub-"+metadata["PatientInfo"]["ID"]
    if ses != "": prefix = prefix + "_ses-"+ses
    prefix = prefix + "_task-" + task
    if acq != "": prefix = prefix + "_acq-"+acq
    if run != "": prefix = prefix + "_run-"+run
    
    logging.info("Copiyng data to folders")
    if eegJson != '':
        shutil.copy2(eegJson, eegPath+"/"+prefix+"_eeg.json")
    if dirName != "":
        shutil.copytree(path, srcPath+"/"+dirName)
    else:
        shutil.copy2(path, srcPath)

    t_ref   = metadata["RecordingInfo"]["StartTime"]
    t_end   = metadata["RecordingInfo"]["StopTime"]
    t_min   = datetime.max
    t_max   = datetime.min

    logging.info("Creating channels.tsv file")
    with open(eegPath+"/"+prefix+"_channels.tsv", "w") as f:
        logging.info("Creating channels.tsv file")
        if eegform == "embla":
            from DataStructure.Channel import Channel
            channels = [Channel(c) for c in glob.glob(path+"/*.ebm")]
            print("name", "type", "units", "description", "sampling_frequency", "reference", 
                "low_cutoff", "high_cutoff", "notch", "status", "status_description", sep='\t', file = f)
            ch_dict = dict()
            
            for c in channels:
                logging.debug("Channel {}, type {}, Sampling {} Hz".format(c.ChannName, c.SigType, int(c.DBLsampling)))

                if c.SigSubType in ch_dict:
                    logging.warning("Channel {} has same sub-type {} as channel {}".format(c.ChannName, c.SigSubType, ch_dict[c.SigSubType].ChannName ))
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
                        logging.warning("Channel '{}': Starts {} sec later than recording {}".format(c.ChannName, (c.Time[0] - t_ref).total_seconds(), t_ref.isoformat()))
                if c.Time[0] < t_min:
                    t_min = c.Time[0]
                    logging.debug("New t_min {}".format(t_min.isoformat()))
                elif c.Time[0] != t_min:
                    logging.warning("Channel '{}': Starts {} sec later than other channels".format(c.ChannName, (c.Time[0] - t_min).total_seconds()))
                if c.Time[-1]+timedelta(0, c._seqSize[-1]*c.DBLsampling, 0) > t_max:
                    t_max = c.Time[-1]+timedelta(0, c._seqSize[-1]/c.DBLsampling, 0) 
                    logging.debug("New t_max {}".format(t_max.isoformat()))
                    
        else:
            raise Exception("EEG format {} not implemented (yet)".format(eegform))

    if t_ref == None:
        t_ref = t_min
    if t_end == None or t_end < t_max:
        t_end = t_max
    logging.info("Start time: {}, Stop time: {}".format(t_ref.isoformat(), t_end.isoformat()))
    logging.info("Earliest time: {}, Latest time: {}".format(t_min.isoformat(), t_max.isoformat()))


    events = []
    logging.info("Creating events.tsv file")
    with open(eegPath+"/"+prefix+"_events.tsv", "w") as f:
        logging.info("Reading events info")
        if eegform == "embla":
            from  Parcel.parcel import Parcel
            evfile = glob.glob(path+"/*.esedb")[0]
            print("onset", "duration", "trial_type", "responce_time", "value", "sample", sep='\t', file = f)
            esedb = olefile.OleFileIO(evfile).openstream('Event Store/Events')
            root = Parcel(esedb)
            evs     = root.get("Events")
            aux_l   = root.getlist("Aux Data")[0]
            grp_l   = root.getlist("Event Groups")[0]
            times   = root.getlist("EventsStartTimes")[0]
            locat   = root.get("Locations", 0)
                
            for ev,time in zip(evs, times):
                logging.debug("Event {}, at {}, loc. {}, aux. {} ".format(ev.EventID, time.strftime("%d/%m/%Y %H:%M:%S.%f"), ev.LocationIdx, ev.AuxDataID))
                try :
                    loc = locat.getlist("Location")[ev.LocationIdx].get("Signaltype").get("SubType") 
                    ch  = ch_dict[loc]
                    dt = (time - ch.Time[0]).total_seconds()
                except:
                    logging.warning("Channel '{}' not in the list of channels".format(loc))
                    ch = None
                    dt = float(ev.LocationIdx) 

                dt = (time - t_ref).total_seconds()

                try:
                    aux = aux_l.get("Aux", ev.AuxDataID).get("Sub Classification History").get("1")
                    name = aux.get("type")
                except:
                    logging.warning("Can't get event name for index {}".format(ev.AuxDataID))
                    aux = None
                    name = "n/a"

                print("%.3f\t%.2f\t%s\tn/a\tn/a"% (dt, ev.TimeSpan, name), file = f, end="")
                if ch != None:
                    print("\t%f"%(dt*ch.DBLsampling), file = f )
                    ch_id = channels.index(ch)
                else:
                    print("\tn/a", file = f)
                    ch_id = 0
                events.append({"Name": name,  "Time":time, "Channel": ch_id, "Span": ev.TimeSpan, "Location": loc})
        else:
            raise Exception("EEG format {} not implemented (yet)".format(eegform))

    outData = None
    if  args.command == "BrainVision":
        logging.info("Converting to BrainVision format")
        outData = BrainVision(eegPath, prefix)
        outData.SetEncoding(args.bv_encoding)
        outData.SetDataFormat(args.bv_format)
        outData.SetEndian(args.bv_endian == "NO")

        logging.info("Creating eeg.vhdr header file")
        for ch in channels:
            outData.Header.CommonInfo.AddFrequency(int(ch.DBLsampling))
            outData.AddChannel(ch.ChannName, '', ch.Gain, ch.CalUnit, "{} at {}".format(ch.SigMainType, ch.SigSubType ))
        outData.Header.write()
        
        logging.info("Creating eeg.vmrk markers file")
        outData.MarkerFile.OpenFile(outData.GetEncoding())
        outData.MarkerFile.SetFrequency(outData.GetFrequency())
        outData.MarkerFile.SetStartTime(t_ref)
        logging.info("Writting new segment events")
        for i,ch in enumerate(channels):
            for t in ch.Time:
                outData.MarkerFile.AddNewSegment(t, i+1)
        logging.info("Writting proper events")
        for ev in events:
            outData.MarkerFile.AddMarker(ev["Name"], ev["Time"], ev["Span"], ev["Channel"], "")
        outData.MarkerFile.Write()

        logging.info("Creating eeg data file")
        outData.DataFile.SetDataFormat(outData.Header.BinaryInfo.BinaryFormat)
        outData.DataFile.SetEndian(outData.Header.BinaryInfo.UseBigEndianOrder)
        outData.DataFile.OpenFile()
        t_e = t_ref
        while True:
            t_s = t_e
            t_e = t_e + timedelta(0,3600,0)
            if t_s >= t_end: break
            if t_e > t_end: t_e = t_end
            logging.info("Timepoint: {}".format(t_s.isoformat()))
            logging.debug("From {} to {} ({})sec.".format(t_s.isoformat(), t_e.isoformat(), (t_e - t_s).total_seconds()))
            l_data = []
            for ch in channels:
                if outData.Header.BinaryInfo.BinaryFormat == "IEEE_FLOAT_32":
                    l_data.append(ch.getValueVector(t_s, t_e, freq_mult=int(outData.GetFrequency()/ch.DBLsampling)))
                else:
                    l_data.append(ch.getValueVector(t_s, t_e, freq_mult=int(outData.GetFrequency()/ch.DBLsampling), raw = True ))
            outData.DataFile.WriteBlock(l_data)

            

    logging.info("All done. Took {} secons".format(tm.process_time()))

except Exception as e:
    logging.error(e)
    traceback.print_exc()
    logging.info("Took {} seconds".format(tm.process_time()))
    exit(1)
