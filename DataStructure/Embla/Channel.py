import struct
import io
from datetime import datetime
import logging

from DataStructure.Generic.Channel import GenChannel

Logger = logging.getLogger("EmblaChannel")


class Field(object):
    """ Class describes type of data and how to read it"""
    __slots__ = ["Name", "Size", "IsText", "Format", "Encoding", "Entries"]

    def __init__(self, Name, Format, Size=0, IsText=False,
                 Encoding="Latin-1", Entries=0, Unique=False):
        self.Name = Name
        self.Format = Format
        self.Size = Size  # 0 -- no size restriction
        self.IsText = IsText
        self.Encoding = Encoding
        if Unique :
            self.Entries = 1
        else:
            self.Entries = Entries

    def __str__(self):
        string = self.Name + ":"
        if (self.IsText):
            string = string + "text (" + self.Encoding + ")"
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
    """ Class containing all information retrieved from ebm file.
    The data instead to be loaded in the memory, 
    are readed directly from file """

    # Minimum and maximum values for short integer
    _MAXINT = 32767
    _MININT = -32767

    """ A dictionary of fields in the ebm file,
    each entry will create a corresponding field in channel class"""
    _Marks = {
        b'\x80\x00\x00\x00' : Field("Version", "B", Size=2, Unique=True),
        b'\x81\x00\x00\x00' : Field("Header", "x", IsText=True, Unique=True),
        b'\x84\x00\x00\x00' : Field("Time", "HBBBBBB", Size=1),
        b'\x85\x00\x00\x00' : Field("Channel", "h", Unique=True),
        b'\x86\x00\x00\x00' : Field("Sampling", "L", Unique=True),
        b'\x87\x00\x00\x00' : Field("Gain", "L", Unique=True),
        b'\x88\x00\x00\x00' : Field("SCount", "I", Unique=True),
        b'\x89\x00\x00\x00' : Field("DBLsampling", "d", Unique=True),
        b'\x8a\x00\x00\x00' : Field("RateCorr", "d", Unique=True),
        b'\x8b\x00\x00\x00' : Field("RawRange", "d", Unique=True),
        b'\x8c\x00\x00\x00' : Field("TransRange", "d", Unique=True),
        b'\x8d\x00\x00\x00' : Field("Channel_32", "H", Unique=True),

        b'\x90\x00\x00\x00' : Field("ChannName", "x",
                                    IsText=True, Unique=True),
        b'\x95\x00\x00\x00' : Field("DMask_16", "h"),
        b'\x96\x00\x00\x00' : Field("SignData", "B", 
                                    Unique=True, Size=1),
        b'\x98\x00\x00\x00' : Field("CalFunc", "x",
                                    IsText=True, Unique=True),
        b'\x99\x00\x00\x00' : Field("CalUnit", "h",
                                    IsText=True, Unique=True),
        b'\x9A\x00\x00\x00' : Field("CalPoint", "h"),

        b'\xa0\x00\x00\x00' : Field("Event", "h"),

        b'\xc0\x00\x00\x00' : Field("SerialNumber", "x",
                                    IsText=True, Unique=True),
        b'\xc1\x00\x00\x00' : Field("DeviceType", "x",
                                    IsText=True, Unique=True),

        b'\xd0\x00\x00\x00' : Field("SubjectName", "x",
                                    IsText=True, Unique=True),
        b'\xd1\x00\x00\x00' : Field("SubjectId", "x",
                                    IsText=True, Unique=True),
        b'\xd2\x00\x00\x00' : Field("SubjectGroup", "x",
                                    IsText=True, Unique=True),
        b'\xd3\x00\x00\x00' : Field("SubjectAtten", "x",
                                    IsText=True, Unique=True),

        b'\xe0\x00\x00\x00' : Field("FilterSet", "h"),
        b'\x20\x00\x00\x00' : Field("Data", "f"),
        b'\x30\x00\x00\x00' : Field("DataGuId", "x",
                                    IsText=True, Unique=True),
        b'\x40\x00\x00\x00' : Field("RecGuId", "x",
                                    IsText=True, Unique=True),

        b'\xA0\x00\x00\x02' : Field("SigType", "h",
                                    IsText=True, Unique=True),
        b'\x20\x00\x00\x04' : Field("LowHight", "d", Unique=True),
        b'\x70\x00\x00\x03' : Field("SigRef", "h",
                                    IsText=True, Unique=True),
        b'\x72\x00\x00\x03' : Field("SigMainType", "h",
                                    IsText=True, Unique=True),
        b'\x74\x00\x00\x03' : Field("SigSubType", "h",
                                    IsText=True, Unique=True),
        b'\xff\xff\xff\xff' : Field("UnknownType", "h")
    } 

    __slots__ = [x.Name for x 
                 in list(_Marks.values())] + [
                         "Endian", "Wide", "_stream",
                         "_seqStart", "_totSize", "_dataSize"]

    def __init__(self, filename):
        super(EbmChannel, self).__init__()
        for f in self.__slots__:
            if f[0:1] != "_":
                setattr(self, f, None)

        self._seqStart = []
        self._totSize = 0
        self._dataSize = 0

        self._stream = open(filename, "rb")
        if not isinstance(self._stream, (io.RawIOBase, io.BufferedIOBase)):
            raise Exception("Stream is not valid")
        self._stream.seek(0)

        # Reading header
        buff = b''
        ch = self._stream.read(1)

        while ch != b'\x1a':
            buff = buff + ch
            ch = self._stream.read(1)

        if (buff.decode('ascii') != 'Embla data file')\
                and (buff.decode('ascii') != 'Embla results file')\
                and (buff.decode('ascii') != 'Embla raw file'):
            raise Exception("We are not reading either Embla results "
                            "or Embla data")
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
                index = index + b'\x00\x00'
            if(index == b''):break
            size = self._stream.read(4)
            size = struct.unpack("<L", size)[0]
            readed = self._read(index, size)
            if (readed != size):
                Logger.warning('In file "{}" at {}'
                               .format(self._stream.name, start))
                Logger.warning("Readed {} bytes, {} expected. "
                               "File seems to be corrupted"
                               .format(readed, size))
                self._stream.seek(0,2)
        self._totSize = sum(self._seqSize)

        # Finalizing initialization
        self._name = self.ChannName
        self._type = self.SigType
        self._id = self.SigMainType + "_" + self.SigSubType
        self._description = self.SigMainType
        if self.SigSubType != "":
            self._description += "-" + self.SigSubType
        self._reference = self.SigRef
        self._unit = self.CalUnit
        self._seqStartTime = self.Time
        self._frequency = int(self.DBLsampling + 0.5)
        if abs(self.DBLsampling / self._frequency - 1) > 1e-4 :
            Logger.warning("{}: Sample frequency is not integer."
                           "Correction factor is 1{:+}"
                           .format(self.GetName(),
                                   self.DBLsampling / self._frequency - 1))
        if (self.RateCorr is not None and self.RateCorr > 1e-4):
            Logger.warning("{}: Sample frequency is not integer. "
                           "Correction factor is 1{:+}"
                           .format(self.GetName(),self.RateCorr))

        self._startTime = self._seqStartTime[0]

        self._digMin = self._MININT
        self._digMax = self._MAXINT

        if (self.RawRange[2] == 0.):
            if (abs(self.RawRange[1]) != abs(self.RawRange[0])):
                self.SetScale(max(abs(self.RawRange[1]),
                                  abs(self.RawRange[0]))
                              / self._digMax)
            else:
                self.SetPhysicalRange(self.RawRange[0], self.RawRange[1])
        else:
            self._digMin = int(self.RawRange[0] / self.RawRange[2])
            self._digMax = int(self.RawRange[1] / self.RawRange[2])
            self.SetScale(self.RawRange[2])
        if isinstance(self.CalFunc, str) and self.CalFunc != "":
            # God help us all
            # x is used implicetly in eval
            Logger.warning("Channel uses calibration function '" 
                           + self.CalFunc + 
                           "'. Actually only linear calibrations "
                           "are supported. If function is not linear, "
                           "retrieved values will be incorrect.")
            x = self.GetPhysMin()
            new_min = eval(self.CalFunc)
            x = self.GetPhysMax()
            new_max = eval(self.CalFunc)
            self.SetPhysicalRange(new_min, new_max)
            # Just for PEP8 conformity
            x

        self.OptimizeMagnitude()

    def __str__(self):
        string = ""
        for f in self.__slots__:
            if f[0:2] == "__":
                f = "_Channel" + f
            attr = getattr(self, f)
            if attr is not None:
                if type(attr) is list:
                    if len(attr) < 5 and len(attr) > 0:
                        if type(attr[0]) is list:
                            string = string + f + '\t'\
                                     + str((attr[0])[0:5]) + '\n'
                        else:
                            string = string + f + '\t'\
                                     + str(attr[0:5]) + '\n'
                    else:
                        string = string + f + '\t[{} entries]\n'\
                                 .format(len(attr))
                else:
                    string = string + f + '\t' + str(getattr(self, f)) + '\n'
        return string

    def __del__(self):
        self._stream.close()

    def _read(self, marker, size):
        start = self._stream.tell()
        if marker not in self._Marks:
            raise KeyError("Marker {} not in the list for channel from {}"
                           .format(marker, self._stream.name))
        dtype = self._Marks[marker]
        fname = dtype.Name 
        fsize = dtype.Size 
        ftype = dtype.Format 
        fenc = dtype.Encoding 
        if getattr(self, fname) is None and not dtype.IsUnique():
            setattr(self, fname, [])
        # tsize represents the a size of the entry, for text it is fixed to 1
        if dtype.IsText:
            tsize = 1
        else:
            tsize = int(struct.calcsize(self.Endian + ftype))
        dsize = size  # Lenth of the field
        nwords = int(dsize / tsize)  # Number of entries in the field

        if fsize > 0 and nwords != fsize:
            raise Exception("Field contains {} words, {} requested"
                            .format(nwords, fsize))

        if dtype.IsText:
            text = self._stream.read(size).decode(fenc).strip('\0')
            if dtype.IsUnique():
                setattr(self, fname, text)
            else:
                setattr(self, fname, getattr(self, fname) + [text])
        else: 
            if fname == "UnknownType":
                # Put warning here: unknown size, corrupted file?
                Logger.warning("Unknown data type")
                # Jumping to EOF
                return self._stream.tell() - start
            if fname == "Data":
                self._seqStart.append(self._stream.tell())
                self._seqSize.append(nwords)
                self._stream.seek(size, 1)
                return self._stream.tell() - start
            dec = self.Endian + ftype * nwords + 'x' * (dsize - tsize * nwords)
            unpacked = struct.unpack(dec, self._stream.read(size))
            if fname == "Version":
                if self.Endian == '>':
                    big, small = unpacked
                else:
                    small, big = unpacked
                if small > 100: small = small / 100
                else: small = small / 10
                self.Version = big + small / 10
            elif fname == "Time":
                year, mon, day, h, m, s, us = unpacked
                time = datetime(year, mon, day, h, m, s, us * 10000)
                self.Time = self.Time + [time]
            else:
                if dtype.IsUnique():
                    if len(unpacked) == 1:
                        setattr(self, fname, unpacked[0])
                    else:
                        setattr(self, fname, list(unpacked))
                else:
                    setattr(self, fname,
                            getattr(self, fname) + [list(unpacked)])
        return self._stream.tell() - start

    def _getValue(self, point, sequence):
        """
        Retrieves value of a particular time point.
        This is reimplementation of Generic _getValue for Embla format
        
        It doesn't check the validity of parameters.

        Parameters
        ----------
        point : int
            the index of the point to be retrieved
        sequence : int
            specifies the sequence in which data will be retrieved

        Returns
        -------
        float or int
            the value of required point
        """

        self._stream.seek(self._seqStart[sequence] + (point) * self._dataSize)
        val = struct.unpack(
                self.Endian + self._Marks[b'\x20\x00\x00\x00'].Format,
                self._stream.read(self._dataSize))[0]
        if val > self._digMax: val = self._digMax
        if val < self._digMin: val = self._digMin
        return val

    def _getValueVector(self, index, size, sequence):
        """
        Reads maximum 'size' points from a given sequence
        starting from index. Will stop at end of sequence

        Parameters
        ----------
        index : int
            a valid index from where data will be read
        size : int
            number of data-points retrieved
        sequence :
            index of sequence to be read from

        Returns
        -------
        list(int)
            a list of readed data

        Raises
        ------
        IOError
            if reaches EOF before reading requested data
        """
        size = min(size, self._seqSize[sequence] - index)
        self._stream.seek(self._seqStart[sequence] + index * self._dataSize)
        data = self._stream.read(self._dataSize * size)
        if len(data) != size * self._dataSize:
            raise IOError("Got {} entries insted of expected {} "
                          "while reading {}".format(len(data), size, 
                                                    self._stream.name)
                          )
        d = struct.unpack(self.Endian
                          + self._Marks[b'\x20\x00\x00\x00'].Format
                          * size, data)
        return d

    def __lt__(self, other):
        if type(other) != type(self):
            raise TypeError("Comparaison arguments must be of the same class")
        if self.Channel_32[1] < other.Channel_32[1]: return True
        if self.Channel_32[1] > other.Channel_32[1]: return False
        return self.Channel_32[0] < other.Channel_32[0]
