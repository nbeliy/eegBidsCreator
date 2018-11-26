import struct
from datetime import datetime

class Event(object):
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
        array.append(Event(data[pos:pos+112]))
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
    
