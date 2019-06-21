############################################################################# 
## wpe is a script that reads Embla event file and prints out the found 
## events together with their occuring times and durations
############################################################################# 
## Copyright (c) 2018-2019, University of Liège
## Author: Nikita Beliy
## Owner: Liege University https://www.uliege.be
## Credits: [{credit_list}]
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
    grp     = root.getlist("Event Types")[0].getlist()
    times   = root.getlist("EventsStartTimes")[0]
    for ev,time in zip(events, times):
        try:
            ev_type = grp[ev.GroupTypeIdx]
        except:
            ev_type = aux.get("Aux",ev.AuxDataID).getlist("Sub Classification History")[0].get("1").get('type')
        print (ev_type, '-', "{0}.{1:03d}".format(time.strftime("%m/%d/%Y %H:%M:%S"),int(time.microsecond/1000 + 0.5)), "({} s)".format(int(ev.TimeSpan)))
    #    print (ev_type, '-', datetime.fromtimestamp(ev.StartTime).strftime("%m/%d/%Y %H:%M:%S.%f"), "({} s)".format(ev.TimeSpan))
