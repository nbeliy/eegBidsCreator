from datetime import datetime, date, timedelta

from fractions import Fraction
from decimal   import Decimal

class Channel(object):
    __slots__ = ["Type", "Specification", "Unit", "Gain", "Scale", "Filter", "Frequency"]
    
    def __init__(self, name, resolution, unit, comments, frequency, Type):
        dec = Fraction(Decimal(str(unit)))
        self.Type = Type
        self.Specification = name
        self.Unit = unit
        self.Gain = dec.numerator
        self.Scale = dec.denumerator
        self.Filter = comments
        self.Frequency = frequency

class EDF(object):
    __slots__ = ["Type", "Patient", "Record", "StartTime", "RecordDuration", "Channels", "Annotations", "Data", "__file", "__path", "__prefix"]

    def __init__(self, path, prefix):
        self.__path = path
        self.__prefix = prefix
        self.__file  = open(path+"/"+prefix+".edf", "wb")
        self.Type    = "EDF+"
        self.Patient = {"Code":"X", "Sex":"X", "Birthdate": "X", "Name":"X"}
        self.Record  = {"StartDate":"X", "Code":"X", "Technician":"X", "Equipment":"X"}
        self.StartTime = datetime.min
        self.RecordDuration = 1.
        self.Channels    = []
        self.Annotations = []
        self.Data        = []


    def AddChannel(self, name, resolution = 1., unit = '', comments = '', frequenct = 1 , Type = ""):
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
        return (self.Patient["Code"].replace(" ","_")+" "+self.Patient["Sex"]+" "+d+" " + self.Patient["Name"].replace(" ","_"))

    def RecordId(self):
        d = ""
        if type(self.Record["StartDate"]) == str:
            d = self.Record["StartDate"].replace(" ", "_")
        elif type(self.Record["StartDate"]) == date:
            self.Record["StartDate"].strftime("%d-%b-%Y")
        else: d = "X"
        return " ".join(["Startdate", d, self.Record["Code"].replace(" ","_"), self.Record["Technician"].replace(" ","_"), self.Record["Equipment"].replace(" ",",")])

    
    def WriteEvents(self):
        if len(self.Annotations) == 0:
            return
        f  = open(self.__path+"/"+self.__prefix+"_events.edf", "wb")
        f.write("{:<8d}".format(0).encode("ascii"))
        f.write("{:<80s}".format(self.PatientId()).encode("ascii"))
        f.write("{:<80s}".format(self.RecordId()).encode("ascii"))
        d = self.StartTime if self.StartTime.year >= 1985 else self.StartTime.replace(year=(self.StartTime.year+ 100))
        f.write("{:<8s}".format(d.strftime("%d.%m.%y")).encode("ascii"))
        f.write("{:<8s}".format(d.strftime("%H.%M.%S")).encode("ascii"))
        f.write("{:<8d}".format(256+256).encode("ascii"))
        f.write("{:<44s}".format("EDF+C").encode("ascii"))
        f.write("{:<8d}".format(1).encode("ascii"))
        f.write("{:<8g}".format(self.RecordDuration).encode("ascii"))
        f.write("{:<4d}".format(1).encode("ascii"))
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
        print(f.tell())
        f.write("{:+f}".format(0).encode("utf_8")+b'\x14\x14'+"Recording starts".encode("utf_8")+b'\x14\x00')
        for ev in self.Annotations:
            print(ev)
            f.write("{:+}".format(ev["Date"]).encode("utf_8"))
            if ev["Duration"] > 0:
                f.write(b'\x15'+"{}".format(ev["Duration"]).encode("utf_8"))
            f.write(b'\x14'+"{}".format(ev["Name"]).encode("utf_8"))
            f.write(b'\x14'+"{}".format('\x14', ev["Description"]).encode("utf_8")+b'\x00')
        
        if f.tell()%2 != 0:
            f.write(b'\x00')
        size = int(f.tell()/2 - 256)
        print (size, f.tell())
        f.seek(pos)
        f.write("{:<8d}".format(size).encode("utf_8"))
        f.close()




    def AddNewSegment(self, date, channel  = 0, description = ''):
        pass
