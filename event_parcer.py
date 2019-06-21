############################################################################# 
## event_parcer is a script that reads Embla event file and prints out
## retrieved information
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
parser = argparse.ArgumentParser(description='Reads embla-formattted events files (.esedb) and printout the retrieved information')

parser.add_argument('infiles', nargs='+',
    metavar='file1, file2',
    help='input files')
args = parser.parse_args()


for fname in args.infiles:
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    print("> File:", fname)
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    esedb = olefile.OleFileIO(fname).openstream('Event Store/Events')

    root = Parcel(esedb)


    events  = root.get("Events")
    aux     = root.getlist("Aux Data")[0]
    grp     = root.getlist("Event Groups")[0]
    times   = root.getlist("EventsStartTimes")[0]
    locat   = root.get("Locations", 0)

    print("##############################")
    print("# Events")
    print("##############################")
    print("Info:", root.get("Info",0))
    for ev,time in zip(events, times):
        print("####################")
        print(ev.EventID)
        print("--------------------")
        print("LocationId:", ev.LocationIdx)
        loc     = locat.get("Location", ev.LocationIdx).get("Signaltype").ls()
        for d in loc:
            print("\t", d.name(), d.read())
        print("--------------------")
        print("AuxDataID:", ev.AuxDataID)
        try:
            loc     = aux.get("Aux", ev.AuxDataID).get("Sub Classification History").get("1").ls()
            for d in loc:
                print("\t", d.name(), d.read())
        except:
            pass
        print("--------------------")
        print("GroupTypeIdx:", ev.GroupTypeIdx)
        try:
            loc     = grp.get("Event Group Type", ev.GroupTypeIdx).ls()
            for d in loc:
                print("\t", d.name(), d.read())
        except:
            pass
        print("--------------------")
        print("StartTime:", datetime.fromtimestamp(ev.StartTime).strftime("%d/%m/%Y %H:%M:%S.%f"))
        print("\t",time.strftime("%d/%m/%Y %H:%M:%S.%f"))
        
        print("--------------------")
        print("TimeSpan:", ev.TimeSpan)
        print("--------------------")
        print("ScoreID:", ev.ScoreID)
        print("--------------------")
        print("CreatorID:", ev.CreatorID)

    print("\n")
    print("##############################")
    print("# Event palettes")
    print("##############################")

    palettes = root.get("Event Palettes", 0)
    print(palettes.ls()[0].name(), palettes.ls()[0].read())
    print("--------------------")
    for p in palettes.getlist("Event Palette"):
        for l in p.ls():
            print("\t", l.name(), l.read()) 
        print("------------------------------")


    print("\n")
    print("##############################")
    print("# Event Types")
    print("##############################")
    palettes = root.get("Event Types", 0)
    for l in palettes.ls():
        print("\t", l.name(), l.read()) 
            
