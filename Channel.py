import struct
from datetime import datetime

#Values: ['Field name', 'data size in words, 0 if unknown, not fixed', 'parcing word, c if it is text',  'encoding string']

class Field(object):
    __slots__ = ["Name", "Size", "IsText", "Format", "Encoding", "Entries"]
    def __init__(self, Name, Format, Size = 0, IsText = False, Encoding = "ascii", Entries = 0, Unique = False):
        self.Name     = Name
        self.Format   = Format
        self.Size     = Size #0 -- no size restriction
        self.IsText   = IsText
        self.Encoding = Encoding
        if Unique :
            self.Entries = 1
        else:
            self.Entries  = Entries
    def __str__(self):
        string = Name + ":"
        if (self.IsText):
            string = string + "text ("+self.Encoding+")"
        else :
            string = string + self.Format       
        if self.Entries == 1:
            string = string + " Unique"
        elif self.Entries > 1 :
            string = string + "{} entries".format(self.Entries)
        return string
    def IsUnique(self):
        return (self.Entries == 1)

Marks = {
    b'\x80\x00\x00\x00' : Field("Version", "B", Size = 2, Unique = True),
    b'\x81\x00\x00\x00' : Field("Header", "x", IsText = True, Unique = True),
    b'\x84\x00\x00\x00' : Field("Time", "HBBBBBB", Size = 1),
    b'\x85\x00\x00\x00' : Field("Channel", "h", Unique = True),
    b'\x86\x00\x00\x00' : Field("Sampling", "L", Unique = True),
    b'\x87\x00\x00\x00' : Field("Gain", "L", Unique = True),
    b'\x88\x00\x00\x00' : Field("SCount", "I", Unique = True),
    b'\x89\x00\x00\x00' : Field("DBLsampling", "d", Unique = True),
    b'\x8a\x00\x00\x00' : Field("RateCorr", "d"),
    b'\x8b\x00\x00\x00' : Field("RawRange", "h"),
    b'\x8c\x00\x00\x00' : Field("TransRange", "h"),
    b'\x8d\x00\x00\x00' : Field("Channel_32", "h"),

    b'\x90\x00\x00\x00' : Field("ChannName", "x", IsText = True, Unique = True),
    b'\x95\x00\x00\x00' : Field("DMask_16", "h"),
    b'\x96\x00\x00\x00' : Field("SignData", "B", Unique = True, Size = 1),
    b'\x98\x00\x00\x00' : Field("CalFunc", "x", IsText = True, Unique = True),
    b'\x99\x00\x00\x00' : Field("CalUnit", "h"),
    b'\x9A\x00\x00\x00' : Field("CalPoint", "h"),
    
    b'\xa0\x00\x00\x00' : Field("Event", "h"),
    
    b'\xc0\x00\x00\x00' : Field("SerialNumber", "x", IsText = True, Unique = True),
    b'\xc1\x00\x00\x00' : Field("DeviceType", "x", IsText = True, Unique = True),
    
    b'\xd0\x00\x00\x00' : Field("SubjectName", "x", IsText = True, Unique = True),
    b'\xd1\x00\x00\x00' : Field("SubjectId", "x", IsText = True, Unique = True),
    b'\xd2\x00\x00\x00' : Field("SubjectGroup", "x", IsText = True, Unique = True),
    b'\xd3\x00\x00\x00' : Field("SubjectAtten", "x", IsText = True, Unique = True),
    
    b'\xe0\x00\x00\x00' : Field("FilterSet", "h"),
    
    b'\x20\x00\x00\x00' : Field("Data", "l"),
    
    b'\x30\x00\x00\x00' : Field("DataGuId", "x", IsText = True, Unique = True),
    b'\x40\x00\x00\x00' : Field("RecGuId", "x", IsText = True, Unique = True),
    
    b'\xA0\x00\x00\x02' : Field("SigType", "h"),
    b'\x20\x00\x00\x04' : Field("LowHight", "h"),
    b'\x70\x00\x00\x03' : Field("SigRef", "h"),
    b'\x72\x00\x00\x03' : Field("SigMainType", "h"),
    b'\x74\x00\x00\x03' : Field("SigSubType", "h"),
   } 
#b'\x1a\x00\x00\x00' : ["SigEnd",        0, ""],
#b'\xff\x00\x00\x00' : ["Invalid",       0, "b"],

class Channel(object):
    __slots__ = [x.Name for x in list(Marks.values())]+["Endian", "Wide"]
    def __init__(self, end, wide):
        for f in self.__slots__:
            setattr(self, f, [])
        self.Endian = end
        self.Wide = wide
        if wide:
            Marks[b'\x20\x00\x00\x00'].Format = 'q'
        else:
            Marks[b'\x20\x00\x00\x00'].Format = 'l'
    
    def __str__(self):
        string = ""
        for f in self.__slots__:
            if getattr(self, f) != None:
                if type(getattr(self, f)) is list:
                    if len(getattr(self, f)) < 5:
                        string = string + f + '\t' + str(getattr(self, f))+ '\n'
                    else:
                        string = string + f + '\t[{} entries]\n'.format(len(getattr(self, f)))
                else:
                    string = string + f + '\t' + str(getattr(self, f))+ '\n'
        return string

    def read(self, marker, data):
        dtype = Marks[marker]
        try:
            fname = dtype.Name
            fsize = dtype.Size
            ftype = dtype.Format
            fenc  = dtype.Encoding
            #tsize represents the a size of the entry, for text it is fixed to 1
            if dtype.IsText:
                tsize = 1
            else:
                tsize = int(struct.calcsize(self.Endian+ftype))
            dsize = len(data)
            nwords = int(dsize/tsize)

            if fsize > 0 and nwords != fsize:
                raise Exception("Field contains {} words, {} requested".format(nwords, fsize))

            if dtype.IsText:
                if dtype.IsUnique():
                    setattr(self, fname, data.decode(fenc).strip('\0'))
                else:
                    setattr(self, fname, getattr(self, fname)+[data.decode(fenc).strip('\0')])
            else:
                dec = self.Endian + ftype*nwords + 'x'*(dsize - tsize*nwords)
                unpacked = struct.unpack(dec, data)
                if fname == "Version":
                    if self.Endian == '>':
                        self.Version = unpacked[0]+unpacked[1]/10
                    else:
                        self.Version = unpacked[1]+unpacked[0]/10
                elif fname == "Time":
                    year, mon, day, h, m, s, us = unpacked
                    time = datetime(year, mon, day, h, m, s, us*10000)
                    self.Time = self.Time+[time]

                else:
                    if dtype.IsUnique():
                        setattr(self, fname, unpacked)
                    else:
                        setattr(self, fname, getattr(self, fname)+[list(unpacked)])

        except Exception as e:
            raise Exception("Unamble to parce {}:{}\n{}".format(dtype[0], data, e))
