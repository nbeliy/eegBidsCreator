import math
from datetime import datetime
from datetime import timedelta
import logging

Logger = logging.getLogger(__name__)


def ReplaceInField(In_string, Void="", ToReplace=None):
    """Find and replace strings in ToReplace tuple 
    in input string. If input string is empty, returns 
    Void string"""

    if not isinstance(In_string, str) or not isinstance(Void, str):
        raise TypeError("ReplaceInField: In_string and Void must be a string")

    if ToReplace is not None:
        if not isinstance(ToReplace, tuple)\
           or len(ToReplace) != 2\
           or not isinstance(ToReplace[0], str)\
           or not isinstance(ToReplace[1], str):
            raise TypeError("ReplaceInField: "
                            "ToReplace must be either None or (str,str)")

    if In_string == "" :
        return Void

    if ToReplace is not None:
        return In_string.replace(ToReplace[0], ToReplace[1])
    return In_string


class GenChannel(object):
    """An intendent virtual class serving as parent to other,
    format specific channel classes."""

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
            raise TypeError(": Source object must be a daughter of "
                            + self.__class__.__name__)
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
    _SIorders = {'Y':24, 'Z':21, 'E':18, 'P':15, 'T':12,'G':9, 
                 'M': 6,'k': 3,'h': 2,'da': 1, 0:'', 'd':-1, 
                 'c':-2, 'm':-3, 'μ':-6, 'n':-9, 'p':-12, 
                 'f':-15, 'a':-18, 'z':21, 'y':-24}

    _BIDStypes = ["AUDIO", "EEG", "HEOG", "VEOG", "EOG", "ECG", "EKG",
                  "EMG", "EYEGAZE", "GSR", "PUPIL", "REF", "RESP", 
                  "SYSCLOCK", "TEMP", "TRIG", "MISC"]

    def __init__(self):
        self._scale = 1.
        self._offset = 0.
        self._unit = ""
        self._magnitude = 0
        self._physMin = self._MINSHORT
        self._physMax = self._MAXSHORT
        self._digMin = self._MINSHORT
        self._digMax = self._MAXSHORT

        self._frequency = 1
        self._name = ""
        self._type = ""
        self._description = ""
        self._reference = ""

        self._seqStartTime = []
        self._seqSize = []

        self._startTime = datetime.min
        self._frMultiplier = 1

        self._baseChannel = self
        self._id = -1

    def GetId(self): return self._id

    def SetId(self, Id): self._id = Id

    def GetScale(self): return self._scale

    def GetOffset(self): return self._offset

    def GetPhysMax(self): return self._physMax

    def GetPhysMin(self): return self._physMin

    def GetDigMax(self): return self._digMax

    def GetDigMin(self): return self._digMin

    def SetScale(self, scale, offset=0):
        """Defining new scale and offset. Physical minimum and maximum
        are recalculated accordingly."""
        if not (isinstance(scale, int) or isinstance(scale, float)):
            raise TypeError("Scale must be integer or float value")
        if not (isinstance(offset, int) or isinstance(offset, float)):
            raise TypeError("Offset must be integer or float value")

        self._scale = scale
        self._offset = offset
        self._physMin = self._fromRaw(self._digMin)
        self._physMax = self._fromRaw(self._digMax)

    def SetPhysicalRange(self, minimum, maximum):
        """Defining new physical extrema.
        The scale and offset are recalculated."""

        if not (isinstance(minimum, int) or isinstance(minimum, float)):
            raise TypeError("Physical mimimum must be "
                            "integer or float value")

        if not (isinstance(maximum, int) or isinstance(maximum, float)):
            raise TypeError("Physical maximum must be "
                            "integer or float value")

        if minimum >= maximum:
            raise ValueError("Physical minimum must be "
                             "lower than maximum")
        self._physMin = minimum
        self._physMax = maximum
        self._calculateScale()

    def SetDigitalRange(self, minimum, maximum):
        """Defining new digital extrema.
        The scale and offset are recalculated."""
        if not (isinstance(minimum, int)):
            raise TypeError("Digital mimimum must be integer value")
        if not (isinstance(maximum, int)):
            raise TypeError("Digital maximum must be integer value")
        if minimum >= maximum:
            raise ValueError("Digital minimum must be lower than maximum")
        if minimum < self._MINSHORT:
            raise ValueError("Digital minimum must be "
                             "greater than minimum short value")
        if maximum > self._MAXSHORT:
            raise ValueError("Digital maximum must be "
                             "greater than maximum short value")

        self._digMin = minimum
        self._digMax = maximum
        self._calculateScale()

    def _calculateScale(self):
        """Recalculates scale and offset 
        according to physical and digital extrema."""
        self._scale = (self._physMax - self._physMin)\
            / (self._digMax - self._digMin)
        self._offset = self._physMin - self._scale * self._digMin

    def FromRaw(self, value):
        """Transform raw short integer value to the measured one.
        Input must be integer and in Digital range."""
        if not (isinstance(value, int)):
            raise TypeError(self.__class__ + ": Value must be an integer")
        if value > self._digMax or value < self._digMin:
            raise Exception(self.__class__
                            + ": value " + str(value) + " out of the range ["
                            + str(self._digMin) + ", "
                            + str(self._digMax) + "]")
        return self._fromRaw(value)

    def _fromRaw(self, value):
        """Transform raw short integer value to the measured one.
        No checks in value performed."""
        return value * self._scale + self._offset

    def ToRaw(self, value):
        """Transform measured value to raw short integer.
        Input must be float and in Physical range."""
        if not (isinstance(value, int) or isinstance(value, float)):
            raise TypeError(self.__class__
                            + ": Value must be an integer or float")
        if value > self._physMax or value < self._physMin:
            raise Exception(self.__class__
                            + ": value " + str(value) + " out of the range ["
                            + str(self._physMin) + ", "
                            + str(self._physMax) + "]")
        return self._toRaw(value)

    def _toRaw(self, value):
        """Transform measured value to raw short integer one.
        No checks in value performed."""
        return int((value - self._offset) / self._scale + 0.5)  

    def SetName(self, name):
        if not (isinstance(name, str)):
            raise TypeError(self.__class__
                            + ": Name must be a string")
        self._name = name

    def GetName(self, Void="", ToReplace=None):
        return ReplaceInField(self._name, Void, ToReplace)

    def SetType(self, name):
        if not (isinstance(name, str)):
            raise TypeError(self.__class__ + ": Type must be a string")
        self._type = name

    def GetType(self, Void="", ToReplace=None):
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
            raise TypeError(self.__class__ + " : Description must be a string")
        self._description = name

    def GetDescription(self, Void="", ToReplace=None):
        return ReplaceInField(self._description, Void, ToReplace)

    def SetReference(self, name):
        if not (isinstance(name, str)):
            raise TypeError(self.__class__ + ": Reference must be a string")
        self._reference = name

    def GetReference(self, Void="", ToReplace=None):
        return ReplaceInField(self._reference, Void, ToReplace)

    def SetUnit(self, unit):
        if not (isinstance(unit, str)):
            raise TypeError(self.__class__ + ": Unit must be a string")
        self._unit = unit

    def GetUnit(self, wMagnitude=True, Void=""):
        if wMagnitude:
            if self._unit == "":
                if self._magnitude == 0:
                    return Void
                else:
                    return "x10^" + str(self._magnitude)

            if self._magnitude in self._SIprefixes:
                return self._SIprefixes[self._magnitude] + self._unit
            else:
                magn = min(self._SIprefixes.keys(),
                           key=lambda k: abs(k - self._magnitude))
                return "x10^" + str(self._magnitude - magn)\
                    + " " + self._SIprefixes[magn] + self._unit
        else:
            if self._unit == "": return Void
            else: return self._unit    

    def SetMagnitude(self, magn):
        """Setting the magnitude to the measured value.
        This affects scale, offset and physical range."""
        if not (isinstance(magn, int)):
            raise TypeError(self.__class__ + ": magnitude must be an integer")
        self._scale /= 10**(magn + self._magnitude)
        self._offset /= 10**(magn + self._magnitude)
        self._physMin /= 10**(magn + self._magnitude)
        self._physMax /= 10**(magn + self._magnitude)
        self._magnitude = magn

    def OptimizeMagnitude(self):
        magn = math.log10(self._scale) + self._magnitude
        if magn < 0 : 
            magn = int(math.floor(magn) / 3 - 0.5 + 1) * 3
        else :
            magn = int(math.ceil(magn) / 3 + 0.5 - 1) * 3
        self.SetMagnitude(magn)

    def GetFrequency(self):
        return self._frequency

    def SetFrequency(self, freq):
        if not isinstance(freq, int):
            raise TypeError("Frequency must be an integer representing Hz")
        self._frequency = freq

    def GetMagnitude(self):
        return self._magnitude 

    """Functions related to the sequences, i.e.
    unenturupted periods of data-taking."""

    def GetNsequences(self):
        """Returns number of interupted sequences"""
        return len(self._seqStartTime)

    def GetSequenceStart(self, seq=0):
        """Returns the start time of the ith sequence"""
        return self._seqStartTime[seq]

    def GetSequenceEnd(self, seq=0):
        return self._seqStartTime[seq]\
            + timedelta(seconds=self.GetSequenceDuration(seq))

    def GetSequenceSize(self, seq=0):
        """Returns the size (number of measurements) in given sequence"""
        return self._seqSize[seq]

    def GetSequenceDuration(self, seq=0):
        """Returns the time span (in seconds) of given sequence"""
        return self._seqSize[seq] / self._frequency

    def SetStartTime(self, start):
        if not isinstance(start, datetime):
            raise TypeError("StartTime must be a datetime object")
        self._startTime = start

    def GetStartTime(self):
        return self._startTime

    def SetFrequencyMultiplyer(self, frMult):
        if not isinstance(frMult,int):
            raise TypeError("Frequency multiplyer must be a positif integer")
        if frMult <= 0:
            raise ValueError("Frequency multiplyer must be positif")
        self._frMultiplier = frMult

    def GetFrequencyMultiplyer(self):
        return self._frMultiplier

    """
    Functions related to the index of a partiular data points.
    Each point can be indexed by global index, common to all channels,
    given the common time origin, and common frequency, or by local index
    defined its position in its sequence.
    """
    def GetIndex(self, sequence, point, StartTime=None, freqMultiplier=None):
        """
        Return global index given sequence, local index,
        reference time and frequency multiplier
        """
        if StartTime is None:
            StartTime = self._startTime
        if freqMultiplier is None:
            freqMultiplier = self._frMultiplier
        if not isinstance(StartTime, datetime):
            raise TypeError("StartTime must be datetime object")
        if not (isinstance(freqMultiplier,int) or freqMultiplier > 0):
            raise TypeError("freqMultiplier must be a positive integer") 
        if not isinstance(sequence, int) or not isinstance(point, int):
            raise TypeError("sequence and point must be integer")
        if sequence < 0 or sequence >= len(self._seqStartTime):
            raise IndexError("sequence (" + str(sequence) 
                             + ")is out of the range")
        if point < 0 or point >= self._seqSize[sequence]:
            raise IndexError("point (" + str(point) 
                             + ")is out of the range")

        time = self._seqStartTime[sequence]\
            - (self._startTime - StartTime).total_seconds()
        return int((time * self._frequency + point) * freqMultiplier)

    def GetTimeIndex(self, index, StartTime=None, freqMultiplier=None):
        """Returns time of corresponding data point"""
        if StartTime is None:
            StartTime = self._startTime
        if freqMultiplier is None:
            freqMultiplier = self._frMultiplier
        if not isinstance(StartTime, datetime):
            raise TypeError("StartTime must be datetime object")
        if not (isinstance(freqMultiplier,int) or freqMultiplier > 0):
            raise TypeError("freqMultiplier must be a positive integer") 
        if not isinstance(index, int):
            raise TypeError("index must be integer")
        if index < 0 :
            raise IndexError("index (" + str(index) + ")is out of the range")
        return StartTime + index / (self._frequency * freqMultiplier)

    def GetIndexTime(self, time, freqMultiplier=None):
        """Returns index of corresponding time """
        if freqMultiplier is None:
            freqMultiplier = 1
        if not (isinstance(freqMultiplier,int) or freqMultiplier > 0):
            raise TypeError("freqMultiplier must be a positive integer") 
        if not isinstance(time, datetime):
            raise TypeError("time must be datetime object")
        return self._getLocalIndex(time, freqMultiplier)

    def GetLocalIndex(self, index, StartTime=None, freqMultiplier=None):
        """Returns the (sequence, loc_index) for given data point.
        If there no valid sequence/index, corresponding value will be -1"""
        if StartTime is None:
            StartTime = self._startTime
        if freqMultiplier is None:
            freqMultiplier = 1
        if not isinstance(StartTime, datetime):
            raise TypeError("StartTime must be datetime object")
        if not (isinstance(freqMultiplier,int) or freqMultiplier > 0):
            raise TypeError("freqMultiplier must be a positive integer") 
        if not isinstance(index, int):
            raise TypeError("index must be integer")
        if index < 0 :
            raise IndexError("index (" + str(index) + ")is out of the range")
        index = math.floor(index / freqMultiplier)
        index -= (self._seqStartTime[0] - StartTime).total_seconds()\
            * self._frequency
        if index < 0 :
            return (-1,-1)
        seq = 0
        while seq < len(self._seqStartTime):
            if index < self._seqSize[seq]:
                return (seq, index)
            seq += 1
            index -= (self._seqStartTime[seq] - self._seqStartTime[seq - 1])\
                * self._frequency  
            if index < 0:
                return (seq,-1)

    def GetValue(self, point, default=0, 
                 sequence=None, StartTime=None, 
                 raw=False):
        """
        Retrieves value of a particular time point. If given hannel is 
        a copy of an original channel, the values are retrieved from 
        the original one. In such case the sequences and start times are
        also treated by original channel.

        This is virtual function, a particular implementation depends
        on daughter class.

        Parameters
        ----------
        point : int 
            the index of the point to be retrieved
            If sequence is not given, a global index is used
        point : datetime
            the time of point to be retrieved
        point : timedelta
            the index of the point to be retrieved 
            by time passed from beginning of sequence
        default : int, 0
            returned value if asked point not available
            e.g. not in sequence
        sequence : int, optional
            specifies the sequence in which data will be retrieved. 
            Points outside given sequence will return default value.
            If pont parameter is given by time, sequence is ignored
        StartTime : datetime, optional
            if point is given by timedelta, specifies the reference time.
            If set to None, the channel-defined value is used.
            If sequence is specified, StartTime is ignored and 
            the beginning of given sequence is used as reference
        raw : bool, False
            If set to true, the raw, unscaled value is retrieved

        Returns
        ---------
        float or int
            the value of required point

        Raises
        --------
        TypeError
            if given parameters are of wrong type
        NotImplementedError
            if class do not implements data retrieval in 
            _getValue function
        """
        # In case of copied channel, all sequences and times are
        # treated by original channel
        if self._baseChannel != self:
            return self._baseChannel.GetValue(point, default,
                                              sequence, StartTime, raw)

        if not (isinstance(point, int) 
                or isinstance(point, datetime) 
                or isinstance(point, timedelta)):
            raise TypeError("point must be either int, datetime or timedelta")
        if not (sequence is None or isinstance(sequence, int)):
            raise TypeError("sequence must be either None or int")
        if not isinstance(raw, bool):
            raise TypeError("raw must be a bool")

        if sequence is not None:
            if StartTime is not None:
                Logger.warning("StartTime is defined together "
                               "with sequence. StartTime will be ignored")
            if sequence < 0 or sequence > self.GetNsequences():
                return default
            StartTime = self.GetSequenceStart(sequence)
        if StartTime is None:
            StartTime = self._startTime

        # point by time
        if isinstance(point, datetime):
            if sequence is not None:
                Logger.warning("sequence parameter is defined "
                               "but point is passed by absolute time. "
                               "sequence will be ignored")
            # converting time to index
            point, sequence = self._getLocalIndex(point)

        # point by timedelta
        elif isinstance(point, timedelta):
            if sequence is not None:
                point = round(point.total_seconds() * self._frequency)
                if point > self.GetSequenceSize(sequence):
                    point = -1
            else:
                point = StartTime + point
                point, sequence = self._getLocalIndex(point)

        # point by index
        else:
            if sequence is not None: 
                if point > self.GetSequenceSize(sequence):
                    point = -1
            else:
                point = self._startTime + timedelta(seconds=point
                                                    / self._frequency)
                point, sequence = self._getLocalIndex(point)

        if point < 0 or sequence < 0:
            return default

        value = self._getValue(point, sequence)
        if raw:
            return value
        else:
            return self._fromRaw(value)

    def _getValue(self, point, sequence):
        """
        Retrieves value of a particular time point.
        This is virtual function and will always raise
        NotImplemented error.

        The reimplementation of function is not expected to check 
        the validity of parameters and ranges.

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

        Raises
        ------
        NotImplementedError
            if _getValue is not implemented for given format
        """
        raise NotImplementedError("_getValue")

    def GetValueVector(self, timeStart, timeEnd, 
                       default=0, freq_mult=None, raw=False):
        """
        Reads and returns datapoints in range [timeStart, timeEnd[.
        The data point coresponding to timeEnd is not retrieved to avoid
        overlaps in sequential reading. If timeEnd - timeStart < 1/frequency
        no data will be readed.

        If given hannel is a copy of an original channel, the values 
        are retrieved from the original one. In such case the sequences 
        and start times are also treated by original channel.

        All values that are output data sequences are filled with 
        default value.

        This functions calls _getValueVector virtual function

        Parameters
        ----------
        timeStart : datetime
            Start time point for reading data
        timeEnd : datetime
            End time point for reading data. Must be equal or bigger than
            timeStart. Data point at timeEnd is not retrieved.
        timeEnd : timedelta
            time range from startTime to be read. Must be positive.
        default : float, 0
            default value for result, if data fals out of sequences
        freq_mult : int, None
            If set, resulting list will be oversampled by this value.
            Each additional cells will be filled with preceeding value
        raw : bool, False
            If set to true, the retrieved values will be unscaled

        Raises
        ------
        TypeError
            if passed parameters are of wrong type
        ValueError
            if timeStart is greater than stopTime
        NotImplemented
            if _getValueVector is not implemented for used format
        """
        if self._baseChannel != self:
            return self._baseChannel.GetValueVector(timeStart, timeEnd,
                                                    default, freq_mult, raw)
        if not (isinstance(timeStart, datetime)):
            raise TypeError("timeStart must be datetime")
        if not (isinstance(timeEnd, datetime)
                or isinstance(timeEnd, timedelta, float)):
            raise TypeError("timeEnd must be either "
                            "datetime, timedelta or float")
        if freq_mult is None:
            freq_mult = 1
        if not (isinstance(freq_mult, int)):
            raise TypeError("freq_mult must be int")
        if not (isinstance(raw, bool)):
            raise TypeError("raw must be boolean")

        dt = timeEnd
        if isinstance(dt, datetime):
            dt = (dt - timeStart).total_seconds()
        elif isinstance(dt, timedelta):
            timeEnd = timeStart + dt
            dt = dt.total_seconds()
        if dt < 0:
            raise ValueError("time span must be positif")

        # total size of data to retrieve
        points = int(dt * self._frequency)
        res = [default] * int(dt * self._frequency * freq_mult)
        seq = -1

        for seq_start, seq_size, seq_time\
                in zip(self._seqStart, self._seqSize, self._seqStartTime):
            seq += 1
            # Sequance starts after end time
            if seq_time >= timeEnd: break
            # offset of sequance start relative to start time
            offset = round((timeStart - seq_time).total_seconds()
                           * self._frequency)

            # Sequence ends before time start
            if (offset) >= seq_size:
                continue

            to_read = 0
            # Index to point in res
            index = 0
            read_start = 0

            # Case 1: sequence started before timeStart, offset is negative
            # We fill from beginning of res list,
            # but reading data from middle of sequence
            if offset >= 0 :
                # number of points to the end of sequence
                to_read = min(seq_size - offset, points)
                read_start = offset

            # Case 2: sequence starts after timeStart, offset is positive
            # We read from start of sequence,
            # but fill in the middle of res vector
            else:
                offset = -offset
                if offset * freq_mult > len(res): break
                to_read = min(seq_size, points - offset)
                index = offset * freq_mult

            d = self._getValueVector(read_start, to_read, seq)
            if len(d) != to_read:
                raise Exception("Sequence {}: readed {} points, "
                                "{} expected".format(
                                    seq, len(d), to_read))
            for i in range(0, to_read):
                # res[index] = struct.unpack(self.Endian\
                #              + self._Marks[b'\x20\x00\x00\x00'].Format,
                #              data[i:i+self._dataSize])[0]
                res[index] = d[i]
                if res[index] > self._digMax: res[index] = self._digMax
                if res[index] < self._digMin: res[index] = self._digMin
                if not raw:
                    res[index] = self._fromRaw(res[index])
                # filling the interpoint space with previous value
                for j in range(index + 1, index + freq_mult):
                    res[j] = res[index]
                index += freq_mult
        return res

    def _getValueVector(self, index, size, sequence):
        """
        Reads maximum size points from a given sequence
        starting from index.

        This is virtual function and will always raise
        NotImplemented error.

        The reimplementation of function is not expected to check 
        the validity of parameters and ranges.

        Parameters
        ----------
        index : int
            a valid index from where data will be read
        size : int
            number of data-points retrieved, will not stop if reaches 
            end of sequence or end of file
        sequence :
            index of sequence to be read from

        Returns
        -------
        list(int)
            a list of readed data
        """
        raise NotImplementedError("_getValueVector")

    def __lt__(self, other):
        """< operator for sorting functions"""
        return self._name < other._name

    def _getLocalIndex(self, time, freqMultiplier=1):
        """
        Retrieves point index and sequence for a given time. If there 
        no corresponding index and/or sequence, will return -1 as 
        corresponding value.

        Do not checks for types

        Parameters
        ----------
        time : datetime
        freqMultiplier : int
            specifies the frequence multiplier for index calculation

        Returns
        -------
        (int, int)
            a tuple of (point, sequence). If time is before the start 
            of first sequence, sequence will be set to -1, else 
            sequence will be the latest sequence before the given time.
            If time is after the sequence end, the index will be set to -1
        """
        ind = -1
        seq = -1
        for t in self._seqStartTime:
            if time < t:
                break
            seq += 1
        if seq >= 0:
            ind = round((time - self.GetSequenceStart(seq)).total_seconds()
                        * self._frequency * freqMultiplier)
            if ind >= self.GetSequenceSize(seq):
                ind = -1
        return (ind, seq)
