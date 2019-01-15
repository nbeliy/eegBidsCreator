import struct, math, io
from datetime import datetime, timedelta

from DataStructure.Generic.Channel import GenChannel

#Values: ['Field name', 'data size in words, 0 if unknown, not fixed', 'parcing word, c if it is text',  'encoding string']

class Field(object):
    """ Class describes type of data and how to read it"""
    __slots__ = ["Name", "Size", "IsText", "Format", "Encoding", "Entries"]
    def __init__(self, Name, Format, Size = 0, IsText = False, Encoding = "Latin-1", Entries = 0, Unique = False):
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
        string = self.Name + ":"
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


class EbmChannel(GenChannel):
    """ Class containing all information retrieved from ebm file. The data instead to be loaded in the memory, are readed directly from file """
    #Minimum and maximum values for short integer
    _MAXINT = 32767
    _MININT = -32767
    """ A dictionary of fields in the ebm file, each entry will create a corresponding field in channel class  """
    _Marks = {
        b'\x80\x00\x00\x00' : Field("Version", "B", Size = 2, Unique = True),
        b'\x81\x00\x00\x00' : Field("Header", "x", IsText = True, Unique = True),
        b'\x84\x00\x00\x00' : Field("Time", "HBBBBBB", Size = 1),
        b'\x85\x00\x00\x00' : Field("Channel", "h", Unique = True),
        b'\x86\x00\x00\x00' : Field("Sampling", "L", Unique = True),
        b'\x87\x00\x00\x00' : Field("Gain", "L", Unique = True),
        b'\x88\x00\x00\x00' : Field("SCount", "I", Unique = True),
        b'\x89\x00\x00\x00' : Field("DBLsampling", "d", Unique = True),
        b'\x8a\x00\x00\x00' : Field("RateCorr", "d", Unique = True),
        b'\x8b\x00\x00\x00' : Field("RawRange", "d", Unique = True),
        b'\x8c\x00\x00\x00' : Field("TransRange", "d", Unique = True),
        b'\x8d\x00\x00\x00' : Field("Channel_32", "H", Unique = True),

        b'\x90\x00\x00\x00' : Field("ChannName", "x", IsText = True, Unique = True),
        b'\x95\x00\x00\x00' : Field("DMask_16", "h"),
        b'\x96\x00\x00\x00' : Field("SignData", "B", Unique = True, Size = 1),
        b'\x98\x00\x00\x00' : Field("CalFunc", "x", IsText = True, Unique = True),
        b'\x99\x00\x00\x00' : Field("CalUnit", "h", IsText=True, Unique = True),
        b'\x9A\x00\x00\x00' : Field("CalPoint", "h"),
        
        b'\xa0\x00\x00\x00' : Field("Event", "h"),
        
        b'\xc0\x00\x00\x00' : Field("SerialNumber", "x", IsText = True, Unique = True),
        b'\xc1\x00\x00\x00' : Field("DeviceType", "x", IsText = True, Unique = True),
        
        b'\xd0\x00\x00\x00' : Field("SubjectName", "x", IsText = True, Unique = True),
        b'\xd1\x00\x00\x00' : Field("SubjectId", "x", IsText = True, Unique = True),
        b'\xd2\x00\x00\x00' : Field("SubjectGroup", "x", IsText = True, Unique = True),
        b'\xd3\x00\x00\x00' : Field("SubjectAtten", "x", IsText = True, Unique = True),
        
        b'\xe0\x00\x00\x00' : Field("FilterSet", "h"),
        
        b'\x20\x00\x00\x00' : Field("Data", "f"),
        
        b'\x30\x00\x00\x00' : Field("DataGuId", "x", IsText = True, Unique = True),
        b'\x40\x00\x00\x00' : Field("RecGuId", "x", IsText = True, Unique = True),
        
        b'\xA0\x00\x00\x02' : Field("SigType", "h", IsText = True, Unique = True),
        b'\x20\x00\x00\x04' : Field("LowHight", "d", Unique = True),
        b'\x70\x00\x00\x03' : Field("SigRef", "h", IsText = True, Unique = True),
        b'\x72\x00\x00\x03' : Field("SigMainType", "h", IsText = True, Unique = True),
        b'\x74\x00\x00\x03' : Field("SigSubType", "h", IsText = True, Unique = True),
    } 
    __slots__ = [x.Name for x in list(_Marks.values())]+["Endian", "Wide", "_stream", "_seqStart", "_totSize", "_dataSize"]


    def __init__(self, filename):
        super(EbmChannel, self).__init__()
        for f in self.__slots__:
            if f[0:1] != "_":
                setattr(self, f, None)

        self._seqStart = []
        self._totSize  = 0
        self._dataSize = 0

        self._stream = open(filename, "rb")
        if not isinstance(self._stream, (io.RawIOBase, io.BufferedIOBase)):
            raise Exception("Stream is not valid")
        self._stream.seek(0)
        #Reading header
        buff = b''
        ch = self._stream.read(1)
        
        while ch != b'\x1a':
            buff = buff+ch
            ch = self._stream.read(1)

        if (buff.decode('ascii') != 'Embla data file') and (buff.decode('ascii') != 'Embla results file')and (buff.decode('ascii') != 'Embla raw file'):
            raise Exception("We are not reading either Embla results or Embla data")
        ch = self._stream.read(1)
        if ch == b'\xff':
            self.Endian = '>'
        elif ch == b'\x00':
            self.Endian = '<'
        else:
            raise Exception("Can't determine endian")

        self.Wide = False
        ch = self._stream.read(1)
        if (ch == b'\xff'):
            ch = self._stream.read(4)
            if ch == b'\xff\xff\xff\xff':   
                self.Wide = True
                self._stream.seek(32 - 6,1)
         
        if self.Wide:
            self._Marks[b'\x20\x00\x00\x00'].Format = 'h'
            self._dataSize = 2
        else:
            self._Marks[b'\x20\x00\x00\x00'].Format = 'b'
            self._dataSize = 1
        
        while True:
            start = self._stream.tell()
            if self.Wide :
                index = self._stream.read(4)
            else:
                index = self._stream.read(2)
                index = index+b'\x00\x00'
            if(index == b''):break
            size = self._stream.read(4)
            size = struct.unpack("<L", size)[0]
            self._read(index, size)
        self._totSize = sum(self._seqSize)

    
        #Finalizing initialization
        self._name         = self.ChannName
        self._type         = self.SigType
        self._id           = self.SigMainType+"_"+self.SigSubType
        self._description  = self.SigMainType
        if self.SigSubType != "":
            self._description += "-"+self.SigSubType
        self._reference    = self.SigRef
        self._unit         = self.CalUnit
        self._seqStartTime = self.Time
        self._frequency    = int(self.DBLsampling)
        self._startTime    = self._seqStartTime[0]


        self._digMin = self._MININT
        self._digMax = self._MAXINT

        if (self.RawRange[2] == 0.):
            if (abs(self.RawRange[1]) !=  abs(self.RawRange[0])):
                self.SetScale(max(abs(self.RawRange[1]), abs(self.RawRange[0])/self._digMax))
            else:
                self.SetPhysicalRange(self.RawRange[0], self.RawRange[1])
        else:
            self._digMin = int(self.RawRange[0]/self.RawRange[2])
            self._digMax = int(self.RawRange[1]/self.RawRange[2])
            self.SetScale(self.RawRange[2])
        if isinstance(self.CalFunc, str) and self.CalFunc != "":
            #God help us all
            x = self.GetPhysMin()
            new_min = eval(self.CalFunc)
            x = self.GetPhysMax()
            new_max = eval(self.CalFunc)
            self.SetPhysicalRange(new_min, new_max)
            
        self.OptimizeMagnitude()
    
    def __str__(self):
        string = ""
        for f in self.__slots__:
            if f[0:2] == "__":
                f = "_Channel"+f
            attr = getattr(self, f)
            if attr != None:
                if type(attr) is list:
                    if len(attr) < 5 and len(attr) > 0:
                        if type(attr[0]) is list:
                            string = string + f + '\t' + str((attr[0])[0:5])+ '\n'
                        else:
                            string = string + f + '\t' + str(attr[0:5])+ '\n'
                    else:
                        string = string + f + '\t[{} entries]\n'.format(len(attr))
                else:
                    string = string + f + '\t' + str(getattr(self, f))+ '\n'
        return string

    def __del__(self):
        self._stream.close()

    def _read(self, marker, size):
        dtype = self._Marks[marker]
        try:
            fname = dtype.Name 
            fsize = dtype.Size 
            ftype = dtype.Format 
            fenc  = dtype.Encoding 
            if getattr(self, fname) == None and not dtype.IsUnique():
                setattr(self, fname, [])
            #tsize represents the a size of the entry, for text it is fixed to 1
            if dtype.IsText:
                tsize = 1
            else:
                tsize = int(struct.calcsize(self.Endian+ftype))
            dsize = size #Lenth of the field
            nwords = int(dsize/tsize) #Number of entries in the field
 
            if fsize > 0 and nwords != fsize:
                raise Exception("Field contains {} words, {} requested".format(nwords, fsize))

            if dtype.IsText:
                text = self._stream.read(size).decode(fenc).strip('\0')
                if dtype.IsUnique():
                    setattr(self, fname, text)
                else:
                    setattr(self, fname, getattr(self, fname)+[text])
            else:
                if fname == "Data":
                    self._seqStart.append(self._stream.tell())
                    self._seqSize.append(nwords)
                    self._stream.seek(size, 1)
                    return
                dec = self.Endian + ftype*nwords + 'x'*(dsize - tsize*nwords)
                unpacked = struct.unpack(dec, self._stream.read(size))
                if fname == "Version":
                    if self.Endian == '>':
                        big, small = unpacked
                    else:
                        small, big = unpacked
                    if small > 100: small = small/100
                    else: small = small/10
                    self.Version = big + small/10
                elif fname == "Time":
                    year, mon, day, h, m, s, us = unpacked
                    time = datetime(year, mon, day, h, m, s, us*10000)
                    self.Time = self.Time+[time]
                else:
                    if dtype.IsUnique():
                        if len(unpacked) == 1:
                            setattr(self, fname, unpacked[0])
                        else:
                            setattr(self, fname, list(unpacked))
                    else:
                        setattr(self, fname, getattr(self, fname)+[list(unpacked)])
        except Exception as e:
            raise Exception("{}: Unamble to parce {}: {}".format(self._stream.name, dtype.Name, e))

    def __GetValue__(self, point, sequence, raw):
        """ Returns value of given measure point. If sequance is given, the point should be in correspondent sequance. If no suequance is given, the point is interpreted as global one """
        if sequence == None:
            point, sequence = self.getRelPoint(point)

        self._stream.seek(self._seqStart[sequence] + (point)*self._dataSize)
        val = struct.unpack(self.Endian+self._Marks[b'\x20\x00\x00\x00'].Format, self._stream.read(self._dataSize))[0]
        if val > self._digMax:
            val = self._digMax
        if val < self._digMin:
            val = self._digMin
        if raw :
            return val
        else:
            return val*self._scale + self._offset

    def __getValueVector__(self, timeStart, timeEnd, default, freq_mult, raw):
        if freq_mult == None:
            freq_mult = self._frMultiplier
        if timeStart > timeEnd:
            raise Exception("Starting time must be lower than ending time")
        if type(freq_mult) != int or freq_mult <= 0:
            raise Exception("Frequance multiplicator must be positve integer")

        #getting list of sequences
        #Points = number of data points to read
        dt = (timeEnd - timeStart).total_seconds()
        points = int(dt*self.DBLsampling)
        #resulting list of size point*freq_mult
        res = [default]*int(dt*self._frequency*freq_mult)

        for  seq_start, seq_size, seq_time in zip(self._seqStart, self._seqSize, self._seqStartTime):
            #Sequance starts after end time
            if seq_time >= timeEnd: break
            #offset of sequance start relative to start time
            offset = int((timeStart - seq_time).total_seconds()*self._frequency)
            if (offset) >= seq_size: #Sequence ends before time start
                continue

            to_read = 0
            #Index to point in res
            index = 0

            #Case 1: sequence started before timeStart, offset is negative
            #We fill from beginning of res list, but reading data from middle of sequence
            if offset >= 0 :
                self._stream.seek(seq_start+offset*self._dataSize)
                #number of points to the end of sequence
                to_read = min(seq_size - offset, points)

            #Case 2: sequence starts after timeStart, offset is positive
            #We read from start of sequence, but fill in the middle of res vector
            else:
                offset = -offset
                if offset*freq_mult > len(res): break
                self._stream.seek(seq_start)
                to_read = min(seq_size, points - offset)
                index = offset*freq_mult

            data = self._stream.read(self._dataSize*to_read)
            if len(data) != self._dataSize*to_read:
                raise Exception("Unexpected end of stream for channel {}, expected {}*{} data, read {}".format(self.ChannName, self._dataSize,to_read, len(data)))
            if len(res) < index+to_read*freq_mult:
                raise Exception("Unexpected end of list for channel {}. Need {}+{}*{} cells, got {}".format(self.ChannName, index, to_read,freq_mult, len(res)))
            d = struct.unpack(self.Endian+self._Marks[b'\x20\x00\x00\x00'].Format*to_read, data)
            for i in range (0, to_read ):
#                res[index] = struct.unpack(self.Endian+self._Marks[b'\x20\x00\x00\x00'].Format, data[i:i+self._dataSize])[0]
                res[index] = d[i]
                if res[index] > self._digMax: res[index] = self._digMax
                if res[index] < self._digMin: res[index] = self._digMin
                if not raw:
                    res[index] = res[index]*self._scale + self._offset
                #filling the interpoint space with previous value
                for j in range(index+1, index+freq_mult):
                    res[j] = res[index]
                index += freq_mult

        return res


    def __lt__(self, other):
        if type(other) != type(self):
            raise TypeError(self.__class__+": Comparaison arguments must be of the same class")
        if self.Channel_32[1] < other.Channel_32[1]: return True
        if self.Channel_32[1] > other.Channel_32[1]: return False
        return self.Channel_32[0] < other.Channel_32[0]

