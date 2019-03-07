import math
from datetime import datetime
from datetime import timedelta
import logging

Logger = logging.getLogger(__name__)

def ReplaceInField(In_string, Void = "", ToReplace = None):
    if not isinstance(In_string, str) or not isinstance(Void, str):
        raise TypeError("ReplaceInField: In_string and Void must be a string")
    if ToReplace != None:
        if not isinstance(ToReplace, tuple) or len(ToReplace) != 2 or not isinstance(ToReplace[0], str) or not isinstance(ToReplace[1], str):
            raise TypeError("ReplaceInField: ToReplace must be either None or (str,str)")
    if In_string == "" :
        return Void
    if ToReplace != None:
        return In_string.replace(ToReplace[0], ToReplace[1])
    return In_string

class GenChannel(object):
    """An intendent virtual class serving as parent to other, format specific channel classes"""
    __base_slots__ = [
        "_scale", "_offset",
        "_unit", "_magnitude",
        "_physMin", "_physMax",
        "_digMin", "_digMax",
        "_seqStartTime",
        "_seqSize",
        "_frequency",
        "_name",
        "_type",
        "_description",
        "_reference",
        "_id",

        "_startTime",
        "_frMultiplier",
        "_baseChannel"
    ]
    __slots__ = __base_slots__

    def __copy__(self, source):
        if not isinstance(source, GenChannel):
            raise TypeError(self.__class__+": Source object must be a daughter of "+self.__class__)
        for f in self.__base_slots__:
            setattr(self, f, getattr(source, f))
        self._baseChannel = source
    
    "Min and max values for an signed short integer"
    _MAXSHORT = 32767
    _MINSHORT = -32768

    """Dictionary of standard SI prefixes, as defined in BIDS"""
    _SIprefixes = {24:'Y', 21:'Z', 18:'E', 15:'P', 12:'T', 9:'G',
                   6:'M', 3:'k', 2:'h', 1:'da', 0:'', -1:'d', 
                   -2:'c', -3:'m', -6:'μ', -9:'n', -12:'p', 
                   -15:'f', -18:'a', -21:'z', -24:'y'}

    """Inverted dictionary of standard SI prefixes, as defined in BIDS"""
    _SIorders   = {'Y':24, 'Z':21, 'E':18, 'P':15, 'T':12,'G':9, 
                   'M': 6,'k': 3,'h': 2,'da': 1, 0:'', 'd':-1, 
                   'c':-2, 'm':-3, 'μ':-6, 'n':-9, 'p':-12, 
                   'f':-15, 'a':-18, 'z':21, 'y':-24}

    _BIDStypes = ["AUDIO", "EEG", "HEOG", "VEOG", "EOG", "ECG", "EKG",
                  "EMG", "EYEGAZE", "GSR", "PUPIL", "REF", "RESP", 
                  "SYSCLOCK", "TEMP", "TRIG", "MISC"]

    def __init__(self):
        self._scale = 1.
        self._offset= 0.
        self._unit  = ""
        self._magnitude = 0
        self._physMin = self._MINSHORT
        self._physMax = self._MAXSHORT
        self._digMin  = self._MINSHORT
        self._digMax  = self._MAXSHORT

        self._frequency = 1
        self._name = ""
        self._type = ""
        self._description = ""
        self._reference   = ""

        self._seqStartTime = []
        self._seqSize      = []
    
        self._startTime    = datetime.min
        self._frMultiplier = 1

        self._baseChannel  = self
        self._id = -1

    def GetId(self): return self._id
    def SetId(self, Id): self._id = Id

    def GetScale(self): return self._scale
    def GetOffset(self): return self._offset
    def GetPhysMax(self): return self._physMax
    def GetPhysMin(self): return self._physMin
    def GetDigMax(self): return self._digMax
    def GetDigMin(self): return self._digMin

    """Defining new scale and offset. Physical minimum and maximum are recalculated accordingly"""
    def SetScale(self, scale, offset = 0):
        if not (isinstance(scale, int) or isinstance(scale, float)):
            raise TypeError(self.__class__+": Scale must be integer or float value")
        if not (isinstance(offset, int) or isinstance(offset, float)):
            raise TypeError(self.__class__+": Offset must be integer or float value")
        self._scale  = scale
        self._offset = offset
        self._physMin = self._fromRaw(self._digMin)
        self._physMax = self._fromRaw(self._digMax)

    """Defining new physical extrema. The scale and offset are recalculated"""
    def SetPhysicalRange(self, minimum, maximum):
        if not (isinstance(minimum, int) or isinstance(minimum, float)):
            raise TypeError(self.__class__+": Physical mimimum must be integer or float value")
        if not (isinstance(maximum, int) or isinstance(maximum, float)):
            raise TypeError(self.__class__+": Physical maximum must be integer or float value")
        if minimum >= maximum:
            raise ValueError(self.__class__+": Physical minimum must be lower than maximum")
        self._physMin = minimum
        self._physMax = maximum
        self._calculateScale()

    """Defining new digital extrema. The scale and offset are recalculated"""
    def SetDigitalRange(self, minimum, maximum):
        if not (isinstance(minimum, int) ):
            raise TypeError(self.__class__+": Digital mimimum must be integer value")
        if not (isinstance(maximum, int) ):
            raise TypeError(self.__class__+": Digital maximum must be integer value")
        if minimum >= maximum:
            raise ValueError(self.__class__+": Digital minimum must be lower than maximum")
        if minimum < self._MINSHORT:
            raise ValueError(self.__class__+": Digital minimum must be greater than minimum short value")
        if maximum > self._MAXSHORT:
            raise ValueError(self.__class__+": Digital maximum must be greater than maximum short value")
        self._digMin = minimum
        self._digMax = maximum
        self._calculateScale()
        
    """Recalculates scale and offset according to physical and digital extrema"""
    def _calculateScale(self):
        self._scale = (self._physMax - self._physMin)/(self._digMax - self._digMin)
        self._offset= self._physMin - self._scale*self._digMin

    """Transform raw short integer value to the measured one. Input must be integer and in Digital range"""
    def FromRaw(self, value):
        if not (isinstance(value, int)):
            raise TypeError(self.__class__+": Value must be an integer")
        if value > self._digMax or value < self._digMin:
            raise Exception(self.__class__+": value "+str(value)+" out of the ranhe ["+str(self._digMin)+", "+str(self._digMax)+"]" )
        return self._fromRaw(value)

    """Transform raw short integer value to the measured one. No checks in value performed"""
    def _fromRaw(self, value):
        return value*self._scale + self._offset

    """Transform measured value to raw short integer. Input must be float and in Physical range"""
    def ToRaw(self, value):
        if not (isinstance(value, int) or isinstance(value, float)):
            raise TypeError(self.__class__+": Value must be an integer or float")
        if value > self._physMax or value < self._physMin:
            raise Exception(self.__class__+": value "+str(value)+" out of the ranhe ["+str(self._physMin)+", "+str(self._physMax)+"]" )
        return self._toRaw(value)

    """Transform measured value to raw short integer one. No checks in value performed"""
    def _toRaw(self, value):
        return int((value - self._offset)/self._scale + 0.5)  
#        return int((value - self._offset)/self._scale)  

    def SetName(self, name):
        if not (isinstance(name, str)):
            raise TypeError(self.__class__+": Name must be a string")
        self._name = name
    def GetName(self, Void = "", ToReplace=None):
        return ReplaceInField(self._name, Void, ToReplace)

    def SetType(self, name):
        if not (isinstance(name, str)):
            raise TypeError(self.__class__+": Type must be a string")
        self._type = name
    def GetType(self, Void = "", ToReplace=None):
        return ReplaceInField(self._type, Void, ToReplace)

    def BidsifyType(self):
        """Replace the type of channel by a BIDS supported type.
        Matching is performed by searching string from _BIDStypes
        in original type. If not found, a MISC type is attributed.
        """
        if self._type == "EKG":
            self._type = "ECG"
        if self._type in self._BIDStypes:
            # Type already BIDS complient
            return

        bids_type = "MISC"
        for t in self._BIDStypes:
            if t in self._type:
                bids_type = t
                break
        if bids_type == "EKG":
            bids_type = "ECG"
        Logger.debug("{}:Changing type from {} to {}".format(
                     self._name, self._type, t))
        self._type = t

    def SetDescription(self, name):
        if not (isinstance(name, str)):
            raise TypeError(self.__class__+": Description must be a string")
        self._description = name
    def GetDescription(self, Void = ""):
        if self._description != "":
            return self._description
        else:
            return Void
    def SetReference(self, name):
        if not (isinstance(name, str)):
            raise TypeError(self.__class__+": Reference must be a string")
        self._reference = name
    def GetReference(self, Void = ""):
        if self._reference != "":
            return self._reference
        else:
            return Void

    def SetUnit(self, unit):
        if not (isinstance(unit, str)):
            raise TypeError(self.__class__+": Unit must be a string")
        self._unit = unit

    def GetUnit(self, wMagnitude = True, Void = ""):
        if wMagnitude:
            if self._unit == "":
                if self._magnitude == 0: return Void
                else: return "x10^"+str(self._magnitude)
            if self._magnitude in self._SIprefixes:
                return self._SIprefixes[self._magnitude]+self._unit
            else:
                magn = min(self._SIprefixes.keys(),key= lambda k: abs(k-self._magnitude))
                return "x10^"+str(self._magnitude - magn)+" "+self._SIprefixes[magn]+self._unit
        else:
            if self._unit == "": return Void
            else: return self._unit    

    """Setting the magnitude to the measured value. This affects scale, offset and physical range"""
    def SetMagnitude(self, magn):
        if not (isinstance(magn, int)):
            raise TypeError(self.__class__+": magnitude must be an integer")
        self._scale    /= 10**(magn+self._magnitude)
        self._offset   /= 10**(magn+self._magnitude)
        self._physMin  /= 10**(magn+self._magnitude)
        self._physMax  /= 10**(magn+self._magnitude)
        self._magnitude = magn

    def OptimizeMagnitude(self):
        magn  = math.log10(self._scale)+self._magnitude
        if magn < 0 : magn = int(math.floor(magn)/3 - 0.5+1)*3
        else :        magn = int(math.ceil(magn)/3  + 0.5-1)*3
        self.SetMagnitude(magn)

    def GetFrequency(self):
        return self._frequency

    def SetFrequency(self, freq):
        if not isinstance(freq, int):
            raise TypeError(self.__class__+": Frequency must be an integer representing Hz")
        self._frequency = freq

    def GetMagnitude(self):
        return self._magnitude 



    """Functions related to the sequences, i.e. unenturupted periods of data-taking."""

    """Returns number of interupted sequences"""
    def GetNsequences(self):
        return len(self._seqStartTime)

    """Returns the start time of the ith sequence"""
    def GetSequenceStart(self, seq = 0):
        return self._seqStartTime[seq]
    def GetSequenceEnd(self, seq = 0):
        return self._seqStartTime[seq]+timedelta(seconds=self.GetSequenceDuration(seq))
    

    """Returns the size (number of measurements) in given sequence"""
    def GetSequenceSize(self, seq = 0):
        return self._seqSize[seq]

    def GetSequenceDuration(self, seq = 0):
        """Returns the time span (in seconds) of given sequence"""
        return self._seqSize[seq]/self._frequency

    def SetStartTime(self, start):
        if not isinstance(start, datetime):
            raise TypeError(self.__class__+": StartTime must be a datetime object")
        self._startTime = start

    def GetStartTime(self):
        return self._startTime

    def SetFrequencyMultiplyer(self, frMult):
        if not isinstance(frMult,int):
            raise TypeError(self._type+": Frequency multiplyer must be a positif integer")
        if frMult <= 0:
            raise ValueError(self._type+": Frequency multiplyer must be positif")
        self._frMultiplier = frMult

    def GetFrequencyMultiplyer(self):
        return self._frMultiplier

    """
    Functions related to the index of a partiular data points.
    Each point can be indexed by global index, common to all channels, given the common time origin, 
    and common frequency, or by local index defined its position in its sequence.
    """
    """
    Return global index given sequence, local index, reference time and frequency multiplier
    """
    def GetIndex(self, sequence, point,  StartTime = None, freqMultiplier = None):
        if StartTime == None:
            StartTime = self._startTime
        if freqMultiplier == None:
            freqMultiplier = self._frMultiplier
        if not isinstance(StartTime, datetime):
            raise TypeError(self.__class__+": StartTime must be datetime object")
        if not (isinstance(freqMultiplier,int) or freqMultiplier > 0):
            raise TypeError(self.__class__+": freqMultiplier must be a positive integer") 
        if not isinstance(sequence, int) or not isinstance(point, int):
            raise TypeError(self.__class__+": sequence and point must be integer")
        if sequence < 0 or sequence >= len(self._seqStartTime):
            raise IndexError(self.__class__+": sequence ("+str(sequence)+")is out of the range")
        if point < 0 or point >= self._seqSize[sequence]:
            raise IndexError(self.__class__+": point ("+str(point)+")is out of the range")
        time = self._seqStartTime[sequence] - (self._startTime - StartTime).total_seconds()
        return int((time*self._frequency+point)*freqMultiplier)
             
    """Returns time of corresponding data point"""
    def GetTimeIndex(self, index, StartTime = None, freqMultiplier = None):
        if StartTime == None:
            StartTime = self._startTime
        if freqMultiplier == None:
            freqMultiplier = self._frMultiplier
        if not isinstance(StartTime, datetime):
            raise TypeError(self.__class__+": StartTime must be datetime object")
        if not (isinstance(freqMultiplier,int) or freqMultiplier > 0):
            raise TypeError(self.__class__+": freqMultiplier must be a positive integer") 
        if not isinstance(index, int):
            raise TypeError(self.__class__+": index must be integer")
        if index < 0 :
            raise IndexError(self.__class__+": index ("+str(point)+")is out of the range")
        return StartTime+index/(self._frequency*freqMultiplier)

    """Returns index of corresponding time """
    def GetIndexTime(self, time, StartTime = None, freqMultiplier = None):
        if StartTime == None:
            StartTime = self._startTime
        if freqMultiplier == None:
            freqMultiplier = self._frMultiplier
        if not isinstance(StartTime, datetime):
            raise TypeError(self.__class__+": StartTime must be datetime object")
        if not (isinstance(freqMultiplier,int) or freqMultiplier > 0):
            raise TypeError(self.__class__+": freqMultiplier must be a positive integer") 
        if not isinstance(time, datetime):
            raise TypeError(self.__class__+": time must be datetime object")
        return int((time - StartTime).total_seconds()*(self._frequency*freqMultiplier))


    """Returns the (sequence, loc_index) for given data point. If there no valid sequence/index, corresponding value will be -1"""
    def GetLocalIndex(self, index, StartTime = None, freqMultiplier = None):
        if StartTime == None:
            StartTime = self._startTime
        if freqMultiplier == None:
            freqMultiplier = self._frMultiplier
        if not isinstance(StartTime, datetime):
            raise TypeError(self.__class__+": StartTime must be datetime object")
        if not (isinstance(freqMultiplier,int) or freqMultiplier > 0):
            raise TypeError(self.__class__+": freqMultiplier must be a positive integer") 
        if not isinstance(index, int):
            raise TypeError(self.__class__+": index must be integer")
        if index < 0 :
            raise IndexError(self.__class__+": index ("+str(point)+")is out of the range")
        index = math.floor(index/freqMultiplier)
        index -= (self._seqStartTime[0] - StartTime).total_seconds()*self._frequency
        if index < 0 :
            return (-1,-1)
        seq = 0
        while seq < len(self._seqStartTime):
            if index < self._seqSize[seq]:
                return (seq, index)
            seq += 1
            index -= (self._seqStartTime[seq] - self._seqStartTime[seq - 1])*self._frequency  
            if index < 0:
                return (seq,-1)

    """Pure virtual functions for retrieving data"""
    def GetValue(self, point, sequence = None, raw = False):
#        if sequence != None:
#            return self.GetValue(self.GetIndex(point, sequence), raw = raw)
        if self._baseChannel == self:
            return self.__getValue__(point, sequence, raw)
        else:
            return self._baseChannel.GetValue(point, sequence, raw)

    def __getValue__(self,point, sequence, raw):
        raise NotImplementedError()

    def GetValueVector(self, timeStart, timeEnd, default=0, freq_mult = None, raw = False):
        if freq_mult == None:
            freq_mult = self._frMultiplier
        if self._baseChannel == self:
            return self.__getValueVector__(timeStart, timeEnd, default, freq_mult, raw)
        else:
            return self._baseChannel.GetValueVector(timeStart, timeEnd, default, freq_mult, raw)

    def __getValueVector__(self, timeStart, timeEnd, default, freq_mult, raw):
        raise NotImplementedError()

    """< operator for sorting functions"""
    def __lt__(self, other):
        if type(other) != type(self):
            raise TypeError(self.__class__+": Comparaison arguments must be of the same class")
        return self._name < other._name
