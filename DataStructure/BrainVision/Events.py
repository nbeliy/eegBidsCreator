from datetime import datetime

class MarkerFile(object):
    __slots__ = ["DataFile", "__file", "__path", "__prefix", "__startTime", "__frequancy", "__mkCount" ]

    def __init__(self, path, prefix, startTime, frequancy, encoding = "ANSII"):
        self.DataFile   = prefix+"_eeg.eeg"
        self.__path     = path
        self.__prefix   = prefix
        self.__startTime= startTime
        self.__frequancy= frequancy
        self.__mkCount  = 0
        
        if encoding == "ANSI":
            enc = "ascii"
        elif encoding == "UTF-8":
            enc = "utf_8"
        else: raise Exception("BrainVision Header: wrong encoding '{}', only 'ANSI' and 'UTF-8' are supported")
        self.__file = open(self.__path+"/"+self.__prefix+"_eeg.vmrk", "w", encoding=enc)
        self.__file.write("Brain Vision Data Exchange Marker File Version 1.0\n")

        self.__file.write("\n[Common Infos]\n")
        self.__file.write("DataFile={}\n".format(self.DataFile))

        self.__file.write("\n[Marker Infos]\n")
        
    def __del__(self):
        self.__file.close()        
       
    def AddNewSegment(self, date, channel  = 0, description = ''):
        self.AddMarker("New Segment", date, 0, channel, description)
        
    def AddMarker(self, name, date, duration = 0, channel = 0, description = '', ) :
        if self.__startTime == datetime.min or self.__frequancy <= 0:
            raise Exception ("Markers start time or frequency are not initialized")
        self.__mkCount += 1
        #<name>,<description>,<position>,<points>,<channel number>,<date>
        pos = int((date - self.__startTime).total_seconds()*self.__frequancy + 0.5)
        lenght = int(duration*self.__frequancy + 0.5)
        if lenght == 0:
            lenght = 1
        self.__file.write("Mk{0}={1},{2},{3},{4},{5},{6}\n".format(
                self.__mkCount,
                name,description,
                pos,lenght,
                channel, 
                date.strftime("%Y%m%d%H%M%S%f") ))
        
        
