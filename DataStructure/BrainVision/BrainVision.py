from DataStructure.BrainVision.Recording import Header 
from DataStructure.BrainVision.Events import MarkerFile
from DataStructure.BrainVision.Data import DataFile

class BrainVision(object):
    __slots__ = ["Header", "MarkerFile", "DataFile"]
    
    def __init__(self, path, prefix, AnonymDate=None):
        self.Header     = Header(path, prefix)
        self.MarkerFile = MarkerFile(path, prefix)
        self.MarkerFile.SetAnonymDate(AnonymDate)
        self.DataFile   = DataFile(path, prefix)

    def SetEncoding(self, encoding):
        encs = ["UTF-8", "ANSI"]
        if encoding not in encs:
            raise Exception("BrainVision: encodind {} is not supported".format(encoding))
        self.Header.CommonInfo.CodePage = encoding
    
    def GetEncoding(self):
        return self.Header.CommonInfo.CodePage

    def SetDataFormat(self, encoding):
        encs = ["IEEE_FLOAT_32", "INT_16", "UINT_16"]
        if encoding not in encs:
            raise Exception("BrainVision: data format {} is not supported".format(encoding))
        self.Header.BinaryInfo.BinaryFormat = encoding
    
    def GetDataFormat(self):
        return self.Header.BinaryInfo.BinaryFormat

    def AddFrequency(self, freq):
        if type(freq) != int:
            raise Exception(__name__+": Only integer frequency is supported")
        self.Header.CommonInfo.AddFrequency(freq)
    def GetFrequency(self):
        return self.Header.CommonInfo.GetFrequency()

    def SetEndian(self, useLittle):
        if useLittle:
            self.Header.BinaryInfo.UseBigEndianOrder = "NO"
        else:
            self.Header.BinaryInfo.UseBigEndianOrder = "YES"

    def AddEvent(self, name, date, duration = 0, channel = 0, description = ''):
        self.MarkerFile.AddMarker(name, date, duration, channel, description)
    
    def AddNewSegment(self, date, channel  = 0, description = ''):
        self.MarkerFile.AddNewSegment(self, date, channel, description)
