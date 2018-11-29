from  Parcel.parcel import Parcel
import olefile
from datetime import datetime

import argparse
parser = argparse.ArgumentParser(description='Reads embla-formattted events file (.esedb) and printout list of events with it timestamp and duration')

parser.add_argument('infiles', nargs='+',
    metavar='file1, file2',
    help='input files')
args = parser.parse_args()


for fname in args.infiles:
    esedb = olefile.OleFileIO(fname).openstream('Event Store/Events')
    root = Parcel(esedb)


    events  = root.get("Events")
    aux     = root.getlist("Aux Data")[0]
    grp     = root.getlist("Event Groups")[0]
    times   = root.getlist("EventsStartTimes")[0]
    for ev,time in zip(events, times):
        try:
            ev_type = aux.get("Aux",ev.AuxDataID).getlist("Sub Classification History")[0].get("1").get('type')
        except:
            ev_type = grp.get("Event Group Type", ev.GroupTypeIdx).get("Group Type")
        print (ev_type, '-', "{}.{}".format(time.strftime("%m/%d/%Y %H:%M:%S"),int(time.microsecond/1000 + 0.5)), "({}".format(ev.TimeSpan), " s)")
    #    print (ev_type, '-', datetime.fromtimestamp(ev.StartTime).strftime("%d/%m/%Y %H:%M:%S.%f"), "({}".format(ev.TimeSpan), "s)")
