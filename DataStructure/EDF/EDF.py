from datetime import datetime, date, timedelta
import struct, math


from DataStructure.Generic.Channel import GenChannel

from fractions import Fraction

class Channel(GenChannel):
    __slots__ = ["_type", "_specification", "_filter"]
    
    def __init__(self, Base = None, Type = "", Specs = "", Filter = ""):
        if isinstance(Base, GenChannel): 
            super(Channel, self).__copy__(Base)
            self._type = Type
            self._specification = Specs
            self._filter = Filter
            if "°" in self._unit:
                self._unit = self._unit[:self._unit.index("°")]+"deg"+ self._unit[self._unit.index("°")+1:]
        else :
            super(Channel, self).__init__()
            self._type = ""
            self._specification = ""
            self._filter = ""

    def Label(self):
        if (self._type in ["EEG", "ECG", "EOG", "ERG", "EMG", "MEG", "MCG"]):
            return self._type+" "+self._name
        else:
            return self._name

    def GetTransducer(self):
        return self._specification

    def GetFilter(self):
        return self._filter

class EDF(object):
    __slots__ = ["Type", "Patient", "Record", "StartTime", "RecordDuration", "Channels", "Annotations", "Data", "__file", "__path", "__prefix","__records"]

    def __init__(self, path, prefix):
        self.__path = path
        self.__prefix = prefix
        self.__file  = None
        self.Type    = "EDF+"
        self.Patient = {"Code":"X", "Sex":"X", "Birthdate": "X", "Name":"X"}
        self.Record  = {"StartDate":"X", "Code":"X", "Technician":"X", "Equipment":"X"}
        self.StartTime = datetime.min
        self.RecordDuration = 1.
        self.Channels    = []
        self.Annotations = []
        self.Data        = []
        self.__records   = 0

    def __del__(self):
        if self.__file != None:
            self.__file.close()

    def SetStartTime(self, starttime):
        self.StartTime = starttime.replace(microsecond=0)

    def AddChannel(self, name, resolution = 1, unit = '', comments = '', frequency = 1 , Type = ""):
        self.Channels.append(Channel(name, resolution, unit, comments, frequency, Type))

    def AddEvent(self, name, date, duration = 0, channel = 0, description = ''):
        ev = {"Name":name, "Date": (date-self.StartTime).total_seconds(), "Duration": duration, "Description":description}
        if len(self.Annotations) == 0 or self.Annotations[-1] != ev:
            self.Annotations.append(ev)

    def PatientId(self):
        d = ""
        if type(self.Record["StartDate"]) == str:
            d = self.Record["StartDate"].replace(" ","_")
        elif type(self.Record["StartDate"]) == date:
            self.Record["StartDate"].strftime("%d-%b-%Y")
        else: d = "X"
        name = self.Patient["Name"]
        if name == self.Patient["Code"]:
            name = "X"
        return (self.Patient["Code"].replace(" ","_")+" "+self.Patient["Sex"]+" "+d+" " + name.replace(" ","_"))[:80]

    def RecordId(self):
        d = ""
        if type(self.Record["StartDate"]) == str:
            d = self.Record["StartDate"].replace(" ", "_")
        elif type(self.Record["StartDate"]) == date:
            self.Record["StartDate"].strftime("%d-%b-%Y")
        else: d = "X"
        return " ".join(["Startdate", d, self.Record["Code"].replace(" ","_"), self.Record["Technician"].replace(" ","_"), self.Record["Equipment"].replace(" ",",")])[:80]

    
    def WriteEvents(self):
        if len(self.Annotations) == 0:
            return
        f  = open(self.__path+"/"+self.__prefix+"_events.edf", "wb")
        self.__writeUpperBlock(f,1)
        f.seek(236,0)
        f.write("{:<8d}".format(1).encode("ascii"))
        f.seek(256)
        f.write("{:<16s}".format("EDF Annotations").encode("ascii"))
        f.write("{:<80s}".format(" ").encode("ascii"))
        f.write("{:<8s}".format(" ").encode("ascii"))
        f.write("{:<8d}".format(-32768).encode("ascii"))
        f.write("{:<8d}".format(32767).encode("ascii"))
        f.write("{:<8d}".format(-32768).encode("ascii"))
        f.write("{:<8d}".format(32767).encode("ascii"))
        f.write("{:<80s}".format(" ").encode("ascii"))

        pos = f.tell()
        f.write("{:<8s}".format(" ").encode("ascii")) #Number of samples in record, to be calculated later
        f.write("{:<32s}".format(" ").encode("ascii"))

        #Start of events
        f.write("{:+f}".format(0).encode("utf_8")+b'\x14\x14'+"Recording starts".encode("utf_8")+b'\x14\x00')
        for ev in self.Annotations:
            f.write("{:+}".format(ev["Date"]).encode("utf_8"))
            if ev["Duration"] > 0:
                f.write(b'\x15'+"{}".format(ev["Duration"]).encode("utf_8"))
            f.write(b'\x14'+"{}".format(ev["Name"]).encode("utf_8"))
            f.write(b'\x14'+"{}".format('\x14', ev["Description"]).encode("utf_8")+b'\x00')
        
        if f.tell()%2 != 0:
            f.write(b'\x00')
        size = int(f.tell()/2 - 256)
        f.seek(pos)
        f.write("{:<8d}".format(size).encode("utf_8"))
        f.close()

    def WriteHeader(self):
        self.__file  = open(self.__path+"/"+self.__prefix+".edf", "wb")
        self.__writeUpperBlock(self.__file, len(self.Channels)+1)
        #[16] Label in format Type Emplacement
        self.__file.write("{:<16s}".format("EDF Annotations").encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<16s}".format(ch.Label()).encode("ascii")[:16])
        #[80] Transducer type
        self.__file.write("{:<80s}".format(" ").encode("ascii")[:80])
        for ch in self.Channels:
            self.__file.write("{:<80s}".format(ch.GetTransducer()).encode("ascii")[:80])
        #[8]    Physical dimensions (i.e. units)
        self.__file.write("{:<8s}".format(" ").encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<8s}".format(ch.GetUnit()).encode("ascii")[:8])
        #[8]    Physical minimum
        self.__file.write("{:<8d}".format(-32768).encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<8f}".format(ch.GetPhysMin()).encode("ascii")[:8])
        #[8]    Physical maximum
        self.__file.write("{:<8d}".format(32767).encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<8f}".format(ch.GetPhysMax()).encode("ascii")[:8])
        #[8]    Digital Minimum
        self.__file.write("{:<8d}".format(-32768).encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<8d}".format(ch.GetDigMin()).encode("ascii"))
        #[8]    Digital maximum
        self.__file.write("{:<8d}".format(32767).encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<8d}".format(ch.GetDigMax()).encode("ascii"))
        #[80]   Prefiltering 
        self.__file.write("{:<80s}".format(" ").encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<80s}".format(ch.GetFilter()).encode("ascii")[:80])
        #[8]    Number of samples per record: Recor duration*Frequency
        self.__file.write("{:<8s}".format("8").encode("ascii")) 
        for ch in self.Channels:
            self.__file.write("{:<8d}".format(int(ch.GetFrequency()*self.RecordDuration)).encode("ascii")[:8]) 
        #[32]   Reserved
        self.__file.write("{:<32s}".format(" ").encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<32s}".format(" ").encode("ascii")[:32])


  
    def __writeUpperBlock(self, f, n_signal):
        #[0-7,8]        Version of data format, always '0'
        f.write("{:<8d}".format(0).encode("ascii"))
        #[8-87, 80]     Local patient identification
        f.write("{:<80s}".format(self.PatientId()).encode("ascii"))
        #[88-167, 80]   Local recording identification
        f.write("{:<80s}".format(self.RecordId()).encode("ascii"))
        #[168-175,8]    Start date (as in metadata)
        d = self.StartTime if self.StartTime.year >= 1985 else self.StartTime.replace(year=(self.StartTime.year+ 100))
        f.write("{:<8s}".format(d.strftime("%d.%m.%y")).encode("ascii"))
        #[176-183,8]    Start time (as in metadata)
        f.write("{:<8s}".format(d.strftime("%H.%M.%S")).encode("ascii"))
        #[184-191,8]    Number of bytes in header
        f.write("{:<8d}".format(256+256*n_signal).encode("ascii"))
        #[192-235,44]   EDF+ identifier ('EDF+C' for continous, 'EDF+D' for discontinious)    
        f.write("{:<44s}".format("EDF+C").encode("ascii"))
#        f.write("{:<44s}".format(" ").encode("ascii"))
        #[236-243,8]    Number of data records, -1 for unknown
        f.write("{:<8d}".format(-1).encode("ascii"))
        #[244-251,8]    Duration of data record   
        f.write("{:<8g}".format(self.RecordDuration).encode("ascii"))
        #[252-255,4]    Number of signals (channels) in record
        f.write("{:<4d}".format(n_signal).encode("ascii"))
        
    def WriteDataBlock(self, data, start):
        if len(data) != len(self.Channels):
            raise Exception("EDF: mismuch data array dimensions")
        records = int(len(data[0])/(self.RecordDuration*self.Channels[0].GetFrequency()))
        total_block_size = 8
        blocks = list()
        for i,c in enumerate(self.Channels):
            if records != int(len(data[i])/(self.RecordDuration*c.GetFrequency())):
                raise Exception(
                        "EDF: {}: number of records ({}) different from other channels ({})".format(
                        c.GetName(), int(len(data[i])/(self.RecordDuration*c.GetFrequency(), records))
                        ))
            blocks.append(int(self.RecordDuration*c.GetFrequency()))
            total_block_size += blocks[-1]

        dt = (start - self.StartTime).total_seconds()
        start_pos = self.__file.tell()
        for r in range(0, records):
            s = self.__file.tell()
            t_stamp  = format(self.RecordDuration*r +dt, '+13f').encode("utf_8").strip()[0:13]
            t_stamp += b'\x14\x14\x00'+b'\x00'*(16 - len(t_stamp) - 3)
            self.__file.write(t_stamp)
            for d, block_size, ch in zip(data, blocks, self.Channels):
                self.__file.write(struct.pack("<"+"h"*block_size, *d[r*block_size:(r+1)*block_size]))
            self.__records += 1
            written = self.__file.tell() - s
            if written != total_block_size*2:
                raise Exception("EDF: Record {} (at {}sec)Written {} bytes, expected to write {}".format(r, dt, written, total_block_size*2))


        written = self.__file.tell() - start_pos
        if written != records*total_block_size*2:
            raise Exception("EDF: Written {} bytes, expected to write {}".format(
                    written, records*total_block_size*2))
        return written
                        
    def Close(self):
        self.__file.seek(236)
        self.__file.write("{:<8d}".format(self.__records).encode("ascii"))
        self.__file.close()
        self.__file = None

    def AddNewSegment(self, date, channel  = 0, description = ''):
        pass
