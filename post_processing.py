import os
import glob
import logging
import json

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

dirs = [os.path.basename(d) for d in glob.glob(path + "/sub-*")]

Logger.info("Reading field definitions")
fields = []
with open(path + "/participants.json", "r") as j:
    fields = list(json.load(j).keys())

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

with open(path + "/participants.tsv", "w") as f:
    print("\t".join(fields), file=f)
    for s in subj:
        if len(fields) != len(s):
            Logger.warning("Subject {} fields mismatch description".format(s[0]))
        print("\t".join(s), end='', file=f)

fields = []
Logger.info("Scnning for scan list")
for sc in glob.glob(path + "/**/*scans.tsv", recursive=True):
    loc_path = os.path.dirname(sc)
    Logger.debug("Scan fount at {}".format(loc_path))
    with open(sc, "r") as f:
        files = [fl.split('\t') for fl in set(f.readlines())]
    files = [fl for fl in files if os.path.isfile(loc_path + "/" + fl[0])]

    with open(sc[:-4] + ".json", "r") as j:
        fields = list(json.load(j).keys())

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
    with open(sc, "w") as f:
        print("\t".join(fields), file=f)
        for s in files:
            if len(fields) != len(s):
                Logger.warning("Scan {} fields mismatch description".format(s[0]))
            print("\t".join(s), end='', file=f)

tools.remove_empty_dirs(path)
