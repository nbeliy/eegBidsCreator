############################################################################# 
## Event contains all nessesary routines to read Embla event files
############################################################################# 
## Copyright (c) 2018-2019, University of Liège
## Author: Nikita Beliy
## Owner: Liege University https://www.uliege.be
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


import struct
from datetime import datetime

class EbmEvent(object):
    """Structure for Event-type data"""
    __slots__ = ["LocationIdx", 
                "AuxDataID", 
                "GroupTypeIdx", 
                "StartTime", 
                "TimeSpan", 
                "ScoreID", 
                "CreatorID",
                "EventID"]

    def __str__(self):
        return self.EventID+" {} {} {} {} {} {} {}".format(self.LocationIdx, self.AuxDataID,
            self.GroupTypeIdx, self.StartTime, self.TimeSpan, self.ScoreID, self.CreatorID)

    def __repr__(self):
        return self.EventID

    def __init__(self, data):
        if len(data) != 32+78+2:
            raise Exception("Event data size is not 78")
        # [0:2] Ushort(H) location index
        # [2:4] Ushort(H) Aux. data
        # [4:8] Uint(I)   GroupType
        # [8:16]double(d) StartTime
        # [16:32]double(d)TimeSpan
        # [32:36]Uint(I)  ScoreID
        # [36:37]char(c)  CreatorID 
        # [37:40] (x)     Unused
        # [32:110] utf_16_le EventID
        # [110:112](x)    Unused 
        parced = struct.unpack("<HHIddIbxxx", data[0:32])
        self.EventID = data[32:32+78].decode('utf_16_le')
        self.LocationIdx = parced[0]
        self.AuxDataID   = parced[1]
        self.GroupTypeIdx= parced[2]
        self.StartTime   = parced[3]
        self.TimeSpan    = parced[4]
        self.ScoreID     = parced[5]
        self.CreatorID   = parced[6]


def ReadEvents(data):
    """Reads and extracts the list of events from data, returns the list of Event objects"""
    if len(data)%112 != 0:
        raise Exception("Data size is not multiple of 112, events record is corrupted")
    array = []
    for pos in range(0, len(data), 112):
        array.append(EbmEvent(data[pos:pos+112]))
    return array

def ReadEventsStartTime(data):
    """Reads and extracts list of starttime from data, return the list of datetime objects"""
    if len(data)%12 != 0:
        raise Exception("Data size is not multiple of 112, events record is corrupted")
    array = []
    for pos in range(0, len(data), 12):
        y,m,d,h,minute,sec,usec = struct.unpack("<HBBBBBxI", data[pos:pos+12])
        array.append(datetime(y,m,d,h,minute, sec, usec))
    return array
    
