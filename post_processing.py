import os
import glob
import logging

import tools.tools as tools

logFormatter = logging.Formatter(
            "[%(levelname)-7.7s]:%(asctime)s:%(name)s %(message)s",
            datefmt='%m/%d/%Y %H:%M:%S')
Logger = logging.getLogger()
Logger.setLevel(getattr(logging, "INFO"))
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
Logger.addHandler(consoleHandler)

Logger.info(">>>>>>>>>>>>>>>>>>>>>>>>")
Logger.info("Starting post-processing")
Logger.info("<<<<<<<<<<<<<<<<<<<<<<<<")
Logger.debug(str(os.sys.argv))
Logger.debug("Process PID: " + str(os.getpid()))

path = os.sys.argv[1]

Logger.info("Path: {}".format(path))

dirs = [os.path.basename(d)[4:] for d in glob.glob(path + "/sub-*")]

Logger.info("Reading subjects list")
f = open(path + "/participants.tsv")
subj = [l.split("\t") for l in set(f.readlines())]
f.close()

subj = [s for s in subj if s[0] in dirs]
subj.sort(key=lambda s: s[0])
if subj == [] or dirs == []:
    raise Exception("Couldn't find subjects in {}".format(path))

subj_names = [s[0] for s in subj]

for d in dirs:
    if d not in subj_names:
        Logger.warning("Subject {} is not in list of participants".format(d))
        tools.rrm(path + "/sub-" + d)

# Add security measure if writ
Logger.info("Writting subject list")
f = open(path + "/participants.tsv", "w")
print("\t".join(["participant_id", "sex", "age"]), file=f)
for s in subj:
    print("\t".join(s), end='', file=f)
f.close()

Logger.info("Scnning for scan list")
for sc in glob.glob(path + "/**/*scans.tsv", recursive=True):
    loc_path = os.path.dirname(sc)
    Logger.debug("Scan fount at {}".format(loc_path))
    f = open(sc, "r")
    files = [fl.split('\t') for fl in set(f.readlines())]
    f.close()
    files = [fl for fl in files if os.path.isfile(loc_path + "/" + fl[0])]

    full_list = glob.glob(loc_path + "/*/*", recursive=True)
    prefixes = []
    for pr in files:
        bn = os.path.basename(pr[0])
        prefixes.append(bn[:bn.rfind('_')])

    for f in full_list:
        found = False
        for pr in prefixes:
            if pr in f: 
                found = True
                break
        if not found:
            Logger.warning("file: {}, prefix not found.".format(f))
            tools.rrm(f)

    files.sort(key=lambda time:time[1])
    f = open(sc, "w")
    print("\t".join(["filename", "acq_time"]), file=f)
    for s in files:
        print("\t".join(s), end='', file=f)
    f.close()

tools.remove_empty_dirs(path)
