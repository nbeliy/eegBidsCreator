import datetime, math


class GenChannel(object):
    """An intendent virtual class serving as parent to other, format specific channel classes"""
    __slots__ = [
        "__scale", "__offset", 
        "__unit", "__magnitude", 
        "__physMin", "__physMax",
        "__digMin", "__digMax",
        "__seqStartTime",
        "__seqSize",
        "__frequency",
        "__name",

        "__startTime",
        "__frMultiplier"
    ]
    
    "Min and max values for an signed short integer"
    __MAXSHORT = 32767
    __MINSHORT = -32768

    "Dictionary of standard SI prefixes (as defined in EDF+ standard)"
    __SIprefixes = {24:'Y', 21:'Z', 18:'E', 15:'P', 12:'T', 9:'G', 6:'M', 3:'K', 2:'H', 1:'D', 0:'', -1:'d', -2:'c', -3:'m', -6:'u', -9:'n', -12:'p', -15:'f', -18:'a', -21:'z', -24:'y'}
    "Inverted dictionary of standard SI prefixes (as defined in EDF+ standard)"
    __SIorders   = {'Y':24, 'Z':21, 'E':18, 'P':15, 'T':12,'G': 9,'M': 6,'K': 3,'H': 2,'D': 1, 0:'', 'd':-1, 'c':-2, 'm':-3, 'u':-6, 'n':-9, 'p':-12, 'f':-15, 'a':-18, 'z':21, 'y':-24}

    def __init__(self):
        self.__scale = 1.
        self.__offset= 0.
        self.__unit  = ""
        self.__magnitude = 0
        self.__physMin = self.__MINSHORT
        self.__physMax = self.__MAXSHORT
        self.__digMin  = self.__MINSHORT
        self.__digMax  = self.__MAXSHORT

        self.__frequency = 1
        self.__name = ""

        self.__seqStartTime = []
        self.__seqSize      = []
    
        self.__StartTime    = datetime.min
        self.__frMultiplier = 1

    def GetScale(self): return self.__scale
    def GetOffset(self): return self.__offset
    def GetPhysMax(self): return self.__physMax
    def GetPhysMin(self): return self.__physMin
    def GetDigMax(self): return self.__digMax
    def GetDigMin(self): return self.__digMin

    """Defining new scale and offset. Physical minimum and maximum are recalculated accordingly"""
    def SetScale(self, scale, offset = 0):
        if not (isinstance(scale, int) or isinstance(scale, float)):
            raise TypeError(self.__type+": Scale must be integer or float value")
        if not (isinstance(offset, int) or isinstance(offset, float)):
            raise TypeError(self.__type+": Offset must be integer or float value")
        self.__scale  = scale
        self.__offset = offset
        self.__physMin = self.__fromRaw(self.__digMin)
        self.__physMax = self.__fromRaw(self.__digMax)

    """Defining new physical extrema. The scale and offset are recalculated"""
    def SetPhysicalRange(self, minimum, maximum):
        if not (isinstance(minimum, int) or isinstance(minimum, float)):
            raise TypeError(self.__type+": Physical mimimum must be integer or float value")
        if not (isinstance(maximum, int) or isinstance(maximum, float)):
            raise TypeError(self.__type+": Physical maximum must be integer or float value")
        if minimum >= maximum:
            raise ValueError(self.__type+": Physical minimum must be lower than maximum")
        self.__physMin = minimum
        self.__physMax = maximum
        self.__calculateOffset()

    """Defining new digital extrema. The scale and offset are recalculated"""
    def SetDigitalRange(self, minimum, maximum):
        if not (isinstance(minimum, int) ):
            raise TypeError(self.__type+": Digital mimimum must be integer or float value")
        if not (isinstance(maximum, int) ):
            raise TypeError(self.__type+": Digital maximum must be integer or float value")
        if minimum >= maximum:
            raise ValueError(self.__type+": Digital minimum must be lower than maximum")
        if minimum < self.__MINSHORT:
            raise ValueError(self.__type+": Digital minimum must be greater than minimum short value")
        if maximum > self.__MAXSHORT:
            raise ValueError(self.__type+": Digital maximum must be greater than maximum short value")
        self.__digMin = minimum
        self.__digMax = maximum
        self.__calculateOffset()
        
    """Recalculates scale and offset according to physical and digital extrema"""
    def __calculateScale(self):
        self.__scale = (self.__physMax - self.__physMin)/(self.__digMax - self.__digMin)
        self.__offset= self.__physMin - self.__scale*self.__digMin

    """Transform raw short integer value to the measured one. Input must be integer and in Digital range"""
    def FromRaw(self, value):
        if not (isinstance(value, int)):
            raise TypeError(self.__type+": Value must be an integer")
        if value > self.__digMax or value < self.__digMin:
            raise Exception(self.__type+": value "+str(value)+" out of the ranhe ["+str(self.__digMin)+", "+str(self.__digMax)+"]" )
        return self.__fromRaw(value)

    """Transform raw short integer value to the measured one. No checks in value performed"""
    def __fromRaw(self, value):
        return value*self.__scale + self.__offset

    """Transform measured value to raw short integer. Input must be float and in Physical range"""
    def ToRaw(self, value):
        if not (isinstance(value, int) or isinstance(value, float)):
            raise TypeError(self.__type+": Value must be an integer or float")
        if value > self.__physMax or value < self.__physMin:
            raise Exception(self.__type+": value "+str(value)+" out of the ranhe ["+str(self.__physMin)+", "+str(self.__physMax)+"]" )
        return self.__toRaw(value)

    """Transform measured value to raw short integer one. No checks in value performed"""
    def __toRaw(self, value):
        return int((value - self.__offset)/self.__scale + 0.5)  


    def SetUnit(self, unit):
        if not (isinstance(unit, str)):
            raise TypeError(self.__type+": Unit must be a string")
        self.__unit = unit

    def GetUnit(self, wMagnitude = True):
        if wMagnitude:
            if self.__unit == "":
                if self.__magnitude == 0: return ""
                else: return "x10^"+str(self.__magnitude)
            if self.__magnitude in self.__SIprefixes:
                return self.__SIprefixes[self.__magnitude]+self.__unit
            else:
                magn = min(self.__SIprefixes.keys(),key= lambda k: abs(k-self.__magnitude)
                return "x10^"+str(self.__magnitude - magn)+" "+self.__SIprefixes[magn]+self.__unit
        else:
            return self.__unit    

    """Setting the magnitude to the measured value. This affects scale, offset and physical range"""
    def SetMagnitude(self, magn):
        if not (isinstance(magn, int)):
            raise TypeError(self.__type+": magnitude must be an integer")
        self.__scale    /= 10**(magn+self.__magn)
        self.__offset   /= 10**(magn+self.__magn)
        self.__physMin  /= 10**(magn+self.__magn)
        self.__physMax  /= 10**(magn+self.__magn)
        self.__magn     = magnitude

    def OptimizeMagnitude(self):
        magn  = math.log10(self.__scale)+self.__magnitude
        if magn < 0 : magn = int(math.floor(magn)/3 - 0.5+1)*3
        else :        magn = int(math.ceil(magn)/3  + 0.5-1)*3
        self.SetMagnitude(magn)

    def GetFrequency(self):
        return self.__frequency

    def SetFrequency(self, freq):
        if not isinstance(freq, int):
            raise TypeError(self.__type+": Frequency must be an integer representing Hz")
        self.__frequency = freq

    def GetMagnitude(self):
        return self.__magnitude 



    """Functions related to the sequences, i.e. unenturupted periods of data-taking."""

    """Returns number of interupted sequences"""
    def GetNsequences(self):
        return len(self.__seqStartTime)

    """Returns the start time of the ith sequence"""
    def GetSequenceStart(self, seq = 0):
        return self.__seqStartTime[seq]

    """Returns the size (number of measurements) in given sequence"""
    def GetSequenceSize(self, seq = 0):
        return self.__seqSize[seq]

    def SetStartTime(self, start):
        if not isinstance(start, datetime):
            raise TypeError(self.__type+": StartTime must be a datetime object")
        self.__startTime = datetime

    def GetStartTime(self):
        return self.__startTime

    def SetFrequencyMultiplyer(self, frMult):
        if not isinstance(frMult,int):
            raise TypeError(self.__type+": Frequency multiplyer must be a positif integer")
        if frMult <= 0:
            raise ValueError(self.__type+": Frequency multiplyer must be positif")
        self.__frMultiplier = frMult

    def GetFrequencyMultiplyer(self):
        return self.__frMultiplier

    """
    Functions related to the index of a partiular data points.
    Each point can be indexed by global index, common to all channels, given the common time origin, 
    and common frequency, or by local index defined its position in its sequence.
    """
    """Return global index given sequence, local index, reference time and frequency multiplier"""
    def GetIndex(self, sequence, point,  StartTime = self.____StartTime, freqMultiplier = self.__frMultiplier):
        if not isinstance(StartTime, datetime):
            raise TypeError(self.__type+": StartTime must be datetime object")
        if not (isinstance(freqMultiplier,int) or freqMultiplier > 0):
            raise TypeError(self.__type+": freqMultiplier must be a positive integer") 
        if not isinstance(sequence, int) or not isinstance(point, int):
            raise TypeError(self.__type+": sequence and point must be integer")
        if sequence < 0 or sequence >= len(self.__seqStartTime):
            raise IndexError(self.__type+": sequence ("+str(sequence)+")is out of the range")
        if point < 0 or point >= self.__seqSize[sequence]:
            raise IndexError(self.__type+": point ("+str(point)+")is out of the range")
        time = self.__seqStartTime[sequence] - (self.__StartTime - StartTime).total_seconds()
        return int((time*self.__frequency+point)*freqMultiplier)
             
    """Returns time of corresponding data point"""
    def GetTimeIndex(self, index, StartTime = self.__StartTime, freqMultiplier = self.__frMultiplier):
        if not isinstance(StartTime, datetime):
            raise TypeError(self.__type+": StartTime must be datetime object")
        if not (isinstance(freqMultiplier,int) or freqMultiplier > 0):
            raise TypeError(self.__type+": freqMultiplier must be a positive integer") 
        if not isinstance(index, int):
            raise TypeError(self.__type+": index must be integer")
        if index < 0 :
            raise IndexError(self.__type+": index ("+str(point)+")is out of the range")
        return StartTime+index/(self.__frequency*freqMultiplier)

    """Returns the (sequence, loc_index) for given data point. If there no valid sequence/index, corresponding value will be -1"""
    def GetLocalIndex(self, index, StartTime = self.__StartTime, freqMultiplier = self.__frMultiplier):
        if not isinstance(StartTime, datetime):
            raise TypeError(self.__type+": StartTime must be datetime object")
        if not (isinstance(freqMultiplier,int) or freqMultiplier > 0):
            raise TypeError(self.__type+": freqMultiplier must be a positive integer") 
        if not isinstance(index, int):
            raise TypeError(self.__type+": index must be integer")
        if index < 0 :
            raise IndexError(self.__type+": index ("+str(point)+")is out of the range")
        index = math.floor(index/freqMultiplier)
        index -= (self.__seqStartTime[0] - StartTime).total_seconds()*self.__frequency
        if index < 0 :
            return (-1,-1)
        seq = 0
        while seq < len(self.__seqStartTime):
            if index < self.__seqSize[seq]:
                return (seq, index)
            seq += 1
            index -= (self.__seqStartTime[seq] - self.__seqStartTime[seq - 1])*self.__frequency  
            if index < 0:
                return (seq,-1)

    """Pure virtual functions for retrieving data"""
    def GetValue(self, point, sequence = None, raw = False):
        return 0.

    def GetValueVector(self, timeStart, timeEnd, default=0, freq_mult = 1, raw = False):
        return []
