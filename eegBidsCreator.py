VERSION = '0.1'

import logging, argparse, os, json, glob, olefile
from datetime import datetime

from DataStructure.Record import ParceRecording

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
parser.add_argument('-j, --json', nargs=1, default='',
    metavar='eegJson', dest='eegJson',
    help = "A json file with task description"
    )
parser.add_argument('-o, --output', nargs=1, default='.', dest='outdir',
    help='destination folder')
parser.add_argument('--log', nargs='?', default='',
    metavar='logfile', dest='logfile',
    help='log ')
parser.add_argument('--quiet, -q', action='store_true', dest='quiet',
    help='suppress terminal output')

parser.add_argument('--verbose', '-v', action='count', dest='verbosity', default=5,
    help='verbosity level')
parser.add_argument('--version', action='version', version='%(prog)s '+VERSION)


args = parser.parse_args()

logging.basicConfig(filemode='w', level=logging.DEBUG,
    format='%(levelname)s:%(asctime)s: %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
if args.logfile != '':
    logging.config.fileConfig(filename=args.logfile, filemode='w')

task    = args.task
acq     = args.acq
ses     = args.ses
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
        logging.info("JSON File: {}".format(eegJson[0]))
        if not os.path.exists(path):
            raise Exception("File {} don't exists".format(path))
        f = open(path)
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
        logging.warning("Directory already exists. Contents will be eraised.")
        rmdir(srcPath)
    
    logging.info("Copiyng data to folders")
    if eegJson != '':
        shutil.copy2(eegJson, eegPath)
    if dirName != "":
        shutil.copytree(path, srcPath+"/"+dirName)
    else:
        shutil.copy2(path, srcPath)
    

except Exception as e:
    logging.error(e)
