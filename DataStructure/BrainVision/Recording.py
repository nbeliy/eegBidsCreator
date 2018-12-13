

class Header(object):
    __slots__ = ["CommonInfo", "AsciiInfo", "BinaryInfo", "Channels", "Comment", "__path", "__prefix"]
    
    def __init__(self, path, prefix, nChannels = 0, sInterval = 0):
        self.CommonInfo = CommonInfo(prefix, nChannels, sInterval)
        self.AsciiInfo  = AsciiInfo()
        self.BinaryInfo = BinaryInfo()
        self.Channels   = list()
        self.Comment    = ""
        self.__path = path
        self.__prefix = prefix
        
    def AddChannel(self, name, reference = '', resolution = 1., unit = '', comments = ''):
        ch = Channel(name)
        ch.Reference = reference
        ch.Resolution= resolution
        ch.Unit     = unit
        ch.Comments = comments
        self.Channels.append(ch)
        self.CommonInfo.NumberOfChannels = len(self.Channels)
        

    def write(self):
        self.CommonInfo.NumberOfChannels  = len(self.Channels)
        self.CommonInfo.SamplingInterval = 1e6/self.CommonInfo.GetFrequency()
        if self.CommonInfo.CodePage == "ANSI":
            enc = "ascii"
        elif self.CommonInfo.CodePage == "UTF-8":
            enc = "utf_8"
        else: raise Exception("BrainVision Header: wrong encoding '{}', only 'ANSI' and 'UTF-8' are supported")
        f = open(self.__path+"/"+self.__prefix+"_eeg.vhdr", "w", encoding=enc)
        f.write("Brain Vision Data Exchange Header File Version 1.0\n")

        f.write("\n[Common Infos]\n")
        
        f.write(self.CommonInfo.printout())
        
        if self.CommonInfo.DataFormat == "BINARY":
            f.write("\n\n[Binary Infos]\n")
            f.write(self.BinaryInfo.printout())
        elif self.CommonInfo.DataFormat == "ASCII":
            f.write("\n\n[ASCII Infos]\n")
            f.write(self.AsciiInfo.printout())
        else: raise Exception("BrainVision Header: Data format '{}' should be either 'BINARY' or 'ASCII'")

        if len(self.Channels) == 0:
            raise Exception("BrainVision Header: List of channels is empty")

        f.write("\n\n[Channel Infos]\n")
        c_count = 1
        for ch in self.Channels:
            f.write("Ch{}={}\n".format(c_count, ch.printout()))
            c_count = c_count+1

        if self.Comment != "":
            f.write("\n\n[Comment]\n")
            f.write(self.Comment)

        f.close()

class CommonInfo(object):
    __slots__ = ["DataFile", "MarkerFile", "DataFormat", "DataOrientation", "DataType", "NumberOfChannels", "SamplingInterval", "Averaged", "AveragedSegments", "SegmentDataPoints", "SegmentationType", "DataPoints", "CodePage", "__freq"]

    def __init__(self, prefix, nChannels = 0, sInterval = 0):
        self.DataFile   = prefix+"_eeg.eeg"
        self.MarkerFile = prefix+"_eeg.vmrk"
        self.DataFormat = "BINARY"
        self.DataOrientation = "MULTIPLEXED"
        self.DataType   = "TIMEDOMAIN"
        self.NumberOfChannels = nChannels
        self.SamplingInterval = sInterval
        self.Averaged   = "NO"
        self.AveragedSegments = 0
        self.SegmentDataPoints= 0
        self.SegmentationType = "NOTSEGMENTED"
        self.DataPoints = 0
        self.CodePage   = "ANSI"
        self.__freq     = 0

    def GetFrequency(self):
        return(self.__freq)

    def SetFrequency(self, freq):
        if type(freq) != int:
            raise TypeError("int expected")
        self.__freq = freq
        self.SamplingInterval = 1e6/freq

    def AddFrequency(self, freq):
        if type(freq) != int:
            raise TypeError("int expected")
        if self.__freq == 0:
            lcd = freq
        else:
            if freq > self.__freq:
                lcd = freq
            else:
                lcd = self.__freq
            while True:
                if (lcd % freq == 0) and (lcd % self.__freq == 0):
                    break
                else:
                    lcd = lcd +1
        
        self.__freq = lcd
        self.SamplingInterval = 1e6/lcd


    def printout(self):
        res = "\n".join([df+"="+str(getattr(self, df)) for df in self.__slots__ if not df.startswith('_')])
        return res


class AsciiInfo(object):
    __slots__ = ["DecimalSymbol", "SkipLines", "SkipColumns", "Channels"]
    
    def __init__(self):
        self.DecimalSymbol  = '.'
        self.SkipLines      = 0
        self.SkipColumns    = 0

    def printout(self):
        res = "\n".join([df+"="+str(getattr(self, df)) for df in self.__slots__ if not df.startswith('_')])
        return res

class Channel(object):
    __slots__ = ["Name", "Reference", "Resolution", "Unit", "Comments"]
    def __init__(self, name):
        self.Name       = name
        self.Reference  = ''
        self.Resolution = 1.
        self.Unit       = ''
        self.Comments   = ''

    def printout(self):
        res = ",".join([str(getattr(self, df)) for df in self.__slots__ if not df.startswith('_')])
        return res

class BinaryInfo(object):
    __slots__ = ["BinaryFormat", "ChannelOffset", "DataOffset", "SegmentHeaderSize", "TrailerSize", "UseBigEndianOrder" ]
    def __init__(self):
        self.BinaryFormat   = "INT_16"
        self.ChannelOffset  = 0 
        self.DataOffset     = 0
        self.SegmentHeaderSize  = 0
        self.TrailerSize    = 0
        self.UseBigEndianOrder  = "NO"

    def printout(self):
        res = "\n".join([df+"="+str(getattr(self, df)) for df in self.__slots__ if not df.startswith('_')])
        #res = ""
        #for df in self.__slots__:
        #    res.append(df+"="+getattr(self, df)+"\n")
        return res


