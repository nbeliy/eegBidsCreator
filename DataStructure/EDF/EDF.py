from datetime import datetime, date, timedelta
import struct, math

from fractions import Fraction
from decimal   import Decimal

class Channel(object):
    __slots__ = ["Type", "Specification", "Unit", "Filter", "Frequency", "__phMin", "__phMax", "__digMin", "__digMax"]
    __prefixes = {24:'Y', 21:'Z', 18:'E', 15:'P', 12:'T', 9:'G', 6:'M', 3:'K', 2:'H', 1:'D', 0:'', -1:'d', -2:'c', -3:'m', -6:'u', -9:'n', -12:'p', -15:'f', -18:'a', -21:'z', -24:'y'}
    __orders   = {'Y':24, 'Z':21, 'E':18, 'P':15, 'T':12,'G': 9,'M': 6,'K': 3,'H': 2,'D': 1, 0:'', 'd':-1, 'c':-2, 'm':-3, 'u':-6, 'n':-9, 'p':-12, 'f':-15, 'a':-18, 'z':21, 'y':-24}
    __MAXINT = 32767
    __MININT = -32768
    
    def __init__(self, name, resolution, unit, comments, frequency, Type):
        #dec = Fraction(Decimal(str(resolution)))
        self.Type = Type
        self.Specification = name
        if "°" in unit:
            unit = unit[:unit.index("°")]+"deg"+ unit[unit.index("°")+1:]
        self.Unit = unit
        self.__digMin = self.__MININT
        self.__digMax =  self.__MAXINT
        self.__phMin  = -( self.__digMax - self.__digMin)*resolution/2
        self.__phMax  = -self.__phMin 
        self.Filter = comments
        self.Frequency = frequency

    def GetPhysExtrema(self):
        return (self.__phMin, self.__phMax)

    def GetDigExtrema(self):
        return (self.__digMin, self.__digMax)

    def SetPhysExtrema(self, minimum, maximum, do_prefix = True):
        if minimum >= maximum:
            raise Exception("EDF: Phisical min {} must be less tham max {}".format(minimum, maximum))
        self.__phMin = minimum
        self.__phMax = maximum
        if do_prefix: self.UpdateUnit()

    def SetDigExtrema(self, minimum, maximum, do_prefix = True):
        if minimum >= maximum:
            raise Exception("EDF: Digital min {} must be less tham max {}".format(minimum, maximum))
        if minimum < self.__MININT:
            raise Exception("EDF: Digital min {} is less than possible minimal value for short int".format(minimum))
        if maximum > self.__MAXINT:
            raise Exception("EDF: Digital max {} is more than possible maximal value for short int".format(maximum))
        self.__digMin = minimum
        self.__digMax = maximum
        if do_prefix: self.UpdateUnit()

    def UpdateUnit(self):
        if self.Unit != "":
            scale = (self.__phMax - self.__phMin)/(self.__digMax - self.__digMin)
            base = 0
            if len(self.Unit) == 2 and self.Unit[0] in self.__orders:
                base = self.__orders[self.Unit[0]]
                self.Unit = self.Unit[1:]
            magn  = math.floor(math.log10(scale))/3
            if magn > 0 : magn = int(magn-0.5)*3
            else: magn = int(magn+0.5)*3
            self.Unit = self.__prefixes[magn+base]+self.Unit
            self.__phMin /= 10**magn
            self.__phMax /= 10**magn
         
        

    def Label(self):
        if (self.Type in ["EEG", "ECG", "EOG", "ERG", "EMG", "MEG", "MCG"]):
            return self.Type+" "+self.Specification
        else:
            return self.Specification

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
        return (self.Patient["Code"].replace(" ","_")+" "+self.Patient["Sex"]+" "+d+" " + self.Patient["Name"].replace(" ","_"))[:80]

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
            self.__file.write("{:<80s}".format(" ").encode("ascii")[:80])
        #[8]    Physical dimensions (i.e. units)
        self.__file.write("{:<8s}".format(" ").encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<8s}".format(ch.Unit).encode("ascii")[:8])
        #[8]    Physical minimum
        self.__file.write("{:<8d}".format(-32768).encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<8f}".format(ch.GetPhysExtrema()[0]).encode("ascii")[:8])
        #[8]    Physical maximum
        self.__file.write("{:<8d}".format(32767).encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<8f}".format(ch.GetPhysExtrema()[1]).encode("ascii")[:8])
        #[8]    Digital Minimum
        self.__file.write("{:<8d}".format(-32768).encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<8d}".format(ch.GetDigExtrema()[0]).encode("ascii"))
        #[8]    Digital maximum
        self.__file.write("{:<8d}".format(32767).encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<8d}".format(ch.GetDigExtrema()[1]).encode("ascii"))
        #[80]   Prefiltering 
        self.__file.write("{:<80s}".format(" ").encode("ascii"))
        for ch in self.Channels:
            self.__file.write("{:<80s}".format(" ").encode("ascii")[:80])
        #[8]    Number of samples per record: Recor duration*Frequency
        self.__file.write("{:<8s}".format("8").encode("ascii")) 
        for ch in self.Channels:
            self.__file.write("{:<8d}".format(int(ch.Frequency*self.RecordDuration)).encode("ascii")[:8]) 
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
        records = int(len(data[0])/(self.RecordDuration*self.Channels[0].Frequency))
        dt = (start - self.StartTime).total_seconds()
        for r in range(0, records):
            t_stamp = "{:+13}".format(dt+r*self.RecordDuration).encode("utf_8").strip()+b'\x14\x14\x00'
            t_stamp += b'\x00'*(16 - len(t_stamp))
            self.__file.write(t_stamp)
            for d,ch in zip(data,self.Channels):
                block_size = int(self.RecordDuration*ch.Frequency)
                #if records != len(d)/block_size:
                #self.__file.write(struct.pack("<"+"h"*block_size, *d[0:block_size]))
                self.__file.write(struct.pack("<"+"h"*block_size, *d[r*block_size:(r+1)*block_size]))
            self.__records += 1
                        
    def Close(self):
        self.__file.seek(236)
        self.__file.write("{:<8d}".format(self.__records).encode("ascii"))
        self.__file.close()
        self.__file = None

    def AddNewSegment(self, date, channel  = 0, description = ''):
        pass
