from datetime import datetime
from datetime import timedelta
import glob
import os
import logging
import bisect
import json

from DataStructure.Generic.Channel import GenChannel as Channel
from DataStructure.Generic.Event import GenEvent as Event

from DataStructure.BIDS.BIDS import BIDSid
from DataStructure.BIDS.BIDS import BIDSfieldLibrary
from DataStructure.BIDS.BIDS import JSONfields

Logger = logging.getLogger(__name__)


class Subject(object):
    __slots__ = ["_id", "Name", "Address", "__gender", "Birth",
                 "Notes", "Height", "Weight", "Head",
                 "BIDSvalues"]
    BIDSfields = BIDSfieldLibrary()

    def __init__(self):
        super(Subject, self).__init__()
        self._id = ""
        self.Name = ""
        self.Address = ""
        self.Gender = 0
        self.Birth = datetime.min
        self.Notes = ""
        self.Height = 0
        self.Weight = 0
        self.Head = 0
        self.BIDSvalues = dict()

    @property
    def ID(self):
        return self._id

    @ID.setter
    def ID(self, value):
        if not isinstance(value, str):
            raise TypeError("value must be a string")
        self._id = value

    @property
    def Gender(self):
        return self.__gender

    @Gender.setter
    def Gender(self, value):
        if value is None:
            self.__gender = 0
            return
        if isinstance(value, str):
            if value in ["H","h", "M", "m"]:
                self.__gender = 2
                return
            if value in ["F", "f", "W", "w"]:
                self.__gender = 1
                return
            raise ValueError("Unknown Gender identification: " + value)
        if isinstance(value, int):
            if value in [0,1,2]:
                self.__gender = value
                return
            raise ValueError("Unknown Gender identification: " + value)
        raise ValueError("Gender identification must be integer or string")


class Device(object):
    __slots__ = ["Type", "ID", "Name", "Manufactor", "Model", "Version"]

    def __init__(self):
        self.Type = ""
        self.ID = ""
        self.Name = ""
        self.Manufactor = ""
        self.Model = ""
        self.Version = ""


class Record(BIDSid):
    __slots__ = ["JSONdata", "SubjectInfo", "DeviceInfo", "Type", 
                 # Time when registrement actually starts and stops
                 "__StartTime", "__StopTime",
                 # Time where the first and last data point are taken
                 "__MinTime", "__MaxTime", 
                 # Time limits concidered for confertion
                 "__RefTime", "__EndTime",
                 "Channels", "_chDict", "_dropped","_mainChannel",
                 "Events",
                 "__Frequency",
                 "__inPath", "__outPath",
                 "_aDate",
                 "_extList",
                 "__locked"
                 "BIDSvalues"]

    BIDSfields = BIDSfieldLibrary()

    @classmethod
    def IsValidInput(cls, inputPath):
        """
        a virtual static method that checks if folder in inputPath is
        a valid input for a subclass

        Parameters
        ----------
        inputPath : str
            path to input folder

        Returns
        -------
        bool
            true if input is valid for given subclass

        Raises
        ------
        TypeError
            if parameters are of invalid type
        FileNotFoundError
            if path not found or is not a directory
        NotImplementedError
            if readers are not defined for given subclass
        """
        if not isinstance(inputPath, str):
            raise TypeError("inputPath must be a string")
        if not os.path.isdir(inputPath):
            raise FileNotFoundError("Path '{}' don't exists "
                                    "or not a directory".format(inputPath))
        return cls._isValidInput(inputPath)

    @staticmethod
    def _isValidInput(inputPath):
        """
        a pure virtual function thats checks if a folder in inputPath is
        a valid input for a subclass

        always rises NotImplementedError

        Parameters
        ----------
        inputPath : str
            path to input folder

        Returns
        -------
        bool
            true if input is valid for given subclass

        Raises
        ------
        NotImplementedError
            if readers are not defined for given subclass
        """
        raise NotImplementedError("virtual _isValidInput not implemented")

    def __init__(self, subject="", 
                 task="", session="", acquisition="",
                 AnonymDate=None):

        # BIDSfieldLibrary.__init__()
        # BIDSid.__init__()
        super().__init__()

        self.__outPath = None
        self.__inPath = None
        self.JSONdata = dict()
        self.SubjectInfo = Subject()
        self.DeviceInfo = Device()
        self.Type = ""
        self.__StartTime = None
        self.__StopTime = None
        self.__MinTime = None
        self.__MaxTime = None
        self.__RefTime = None
        self.__EndTime = None

        self.Channels = list()
        self._mainChannel = None
        self.Events = list()
        self._chDict = dict()
        self._dropped = list()
        self.__Frequency = 1
        self._aDate = AnonymDate

        self._extList = []

        self.BIDSvalues = dict()

    ##################
    # Path and files # 
    ##################

    def SetInputPath(self, inputPath):
        """
        sets the path to directory of source files. inputPath must 
        exist and be a directory. All source files are expected 
        to be found inside

        Always ends with '/'

        Parameters
        ----------
        inputPath : str
            path to the input directory

        Returns
        -------
        str
            absolute input path

        Raises
        ------
        TypeError
            if parameters are of invalid type
        FileNotFoundError
            if input path do not exists
        """
        if not isinstance(inputPath, str):
            raise TypeError("inputPath must be a string")
        if not os.path.isdir(inputPath):
            raise FileNotFoundError("Invalid path ''".format(inputPath))
        self.__inPath = os.path.realpath(inputPath) + '/'
        return self.__inPath

    def SetOutputPath(self, outputPath):
        """
        sets the output path within a directory given in outputPath variable

        Parameters
        ----------
        outputPath: str
            root path to strore folder

        Returns
        -------
        str
            the setted output path

        Raises
        ------
        TypeError
            if provided options are of incorrect type
        FileNotFoundError
            if output path do not exists
        ValueError
            if record is locked
        """
        if not isinstance(outputPath, str):
            raise TypeError("outputPath must be a string")
        if self.IsLocked():
            raise ValueError("record is locked")
        if not os.path.isdir(outputPath): 
            raise FileNotFoundError("Output folder {} don't exists."
                                    .format(outputPath))
        self.__outPath = os.path.realpath(outputPath)
        Logger.info("Output will be found at '{}'".format(self.__outPath))
        return self.__outPath

    def GetInputPath(self, appendix=""):
        """
        returns the path to input directory with an attached appendix
        Do not checks if path with appendix exists

        Parameters
        ----------
        appendix : str
            appendix to attach to the path

        Returns
        -------
        str
            path with attached appendix

        Raises
        ------
        TypeError
            if parameters are of invalid type
        """
        if not isinstance(appendix, str):
            raise TypeError("appendix must be a string")
        return os.path.join(self.__inPath, appendix)

    def GetOutputPath(self):
        """
        provides output root directory
        """
        return self.__outPath

    def Path(self, predir="", appdir="", appfile=""):
        """
        generates a path string in the output folder of the form
        'outputFolder[/predir]/innerPath[/appdir]/[appfile]'
        If file not specified returned path ends with '/'

        Record IDs must be locked prior using this function

        Parameters
        ----------
        predir : str
            prefix to add to the path
        appdir : str
            appendix to add to the path
        appfile: str
            file to add to the path

        Returns
        -------
        str
            path string

        Raises
        ------
        TypeError
            if passed parameters are of wrong type
        ValueError
            if record is not locked
        """
        if not isinstance(predir, str):
            raise TypeError("predir must be a string")
        if not isinstance(appdir, str):
            raise TypeError("appdir must be a string")
        if not isinstance(appfile, str):
            raise TypeError("appfile must be a string")
        if not self.IsLocked():
            raise ValueError("Record IDs must be locked prior acessing paths")
        path = os.path.join(self.__outPath, predir,
                            self.GetInnerPath(), appdir, appfile)
        path = os.path.normpath(path)
        if appfile == "":
            path += '/'
        return path

    def GetAuxFiles(self, path=None):
        """
        provides a list of paths to the auxiliary files in path directory.
        File is considered as auxiliary if his extention is not in list of
        assotiated extentions (_extList)

        Parameters
        ----------
        path, str
            path to eeg files

        Returns
        -------
        list(str)
            list of paths to auxiliary files

        Raises
        ------
        TypeError
            if provided options are of incorrect type
        """
        if path is None:
            path = self.__inPath
        if not isinstance(path, str):
            raise TypeError("Path must be a string")
        return [os.path.basename(f) 
                for f in glob.glob(path + "/*") 
                if not os.path.splitext(f)[1] in self._extList 
                ]

    def GetMainFiles(self, path=None):
        """
        provides a list of paths to the eeg files in path directory.
        File is considered as eeg file if his extention is in list of
        assotiated extentions (_extList)

        Parameters
        ----------
        path, str
            path to eeg files

        Returns
        -------
        list(str)
            list of paths to eeg files

        Raises
        ------
        TypeError
            if provided options are of incorrect type
        """
        if path is None:
            path = self.__inPath
        if not isinstance(path, str):
            raise TypeError("Path must be a string")
        return [os.path.basename(f) 
                for f in glob.glob(path + "/*") 
                if os.path.splitext(f)[1] in self._extList 
                ]

    ###############################
    # Frequency related functions #
    ###############################

    @property
    def Frequency(self): return self.__Frequency

    @Frequency.setter
    def Frequency(self, value):
        if not isinstance(value, int):
            raise TypeError("value must be an int")
        if value <= 0 :
            raise ValueError("Frequency must be positive non null value")
        self.__Frequency = value

    def AddFrequency(self, value):
        if not isinstance(value, int):
            raise TypeError("value must be an int")
        if value <= 0 :
            raise ValueError("Frequency must be positive non null value")
        if self.__Frequency == 0 or value == self.__Frequency:
            self.__Frequency = value
            return
        lcd = min(self.__Frequency, value)
        while (lcd % value != 0) or (lcd % self.__Frequency != 0):
            lcd += 1
        self.__Frequency = lcd

    ##########################
    # Time-related functions #
    ##########################

    def SetStartTime(self, t_start=None, t_end=None):
        """
        sets recording start/end times to given values

        There is three kind of time range:
        Start/Stop time: the recording time as specified in header
        Reference/End time: time range which serves as reference for
            data samples. There will be no data outside this range
        Min/Max time: time interval coresponding to first-last 
            data taken

        Parameters
        ----------
        t_start: datetime
            the start time value
        t_end: datetime
            the end time value

        Returns
        -------
        (datetime, datetime)
            a tuple of start/stop time

        Raises
        ------
        TypeError
            if passed parameters are of incorrect type
        ValueError
            if stop time is less than start time
        """
        if t_start and not isinstance(t_start, datetime):
            raise TypeError("Start time must be a datetime object")
        if t_end and not isinstance(t_end, datetime):
            raise TypeError("Stop time must be a datetime object")
        if t_start == datetime.min or t_start == datetime.max: t_start = None
        if t_end == datetime.min or t_end == datetime.max: t_end = None 
        if t_start and t_end:
            if t_start > t_end:
                raise ValueError("Start time must be earlyer than stop time")
        self.__StartTime = t_start
        self.__StopTime = t_end
        return (self.__StartTime, self.__StopTime)

    def SetReferenceTime(self, t_ref=None, t_end=None):
        """
        sets recording reference times to given values
        if the time is not specified, will be set to in order
        Start/Stop or Min/Max time

        There is three kind of time range:
        Start/Stop time: the recording time as specified in header
        Reference/End time: time range which serves as reference for
            data samples. There will be no data outside this range
        Min/Max time: time interval coresponding to first-last 
            data taken

        Parameters
        ----------
        t_start: datetime
            the reference time value
        t_end: datetime
            the end time value

        Returns
        -------
        (datetime, datetime)
            a tuple of reference/end time

        Raises
        ------
        TypeError
            if passed parameters are of incorrect type
        ValueError
            if stop time is less than start time
        """
        if t_ref == datetime.min or t_ref == datetime.max: t_ref = None
        if t_end == datetime.min or t_end == datetime.max: t_end = None

        if t_ref:
            self.__RefTime = t_ref
        elif self.__RefTime is not None:
            pass
        elif self.__StartTime is not None:
            self.__RefTime = self.__StartTime
        elif self._mainChannel is not None:
            self.__RefTime = self._mainChannel.GetSequenceStart(0)
        else:
            self.__RefTime = self.__MinTime
        if t_end:
            self.__EndTime = t_end
        elif self.__EndTime is not None:
            pass
        elif self.__StopTime is not None:
            self.__EndTime = self.__StopTime
        elif self._mainChannel is not None:
            self.__EndTime = self._mainChannel.GetSequenceEnd(-1)
        else:
            self.__EndTime = self.__MaxTime
        return (self.__RefTime, self.__EndTime)

    def CropTime(self, t_low=None, t_high=None, verbose=False):
        """
        reduces the reference time to given values, if values are 
        None or outside of actual reference times, reference 
        will remain unchainged is performed. 

        To enlarge reference interval use SetReferenceTime
        """
        if t_low == datetime.min or t_low == datetime.max: t_low = None
        if t_high == datetime.min or t_high == datetime.max: t_high = None

        old_duration = self.__EndTime - self.__RefTime
        if t_low and t_low > self.__RefTime: 
            if verbose:
                Logger.info("Cropping reference time by {}"
                            .format(self.__RefTime - t_low))
                Logger.debug("from {} to {}".format(
                    self._returnTime(self.__RefTime, True), 
                    self._returnTime(t_low, True)))
            self.__RefTime = t_low 
        if t_high and t_high > self.__EndTime: 
            if verbose:
                Logger.info("Cropping end time by {}"
                            .format(self.__EndTime - t_high))
                Logger.debug("from {} to {}".format(
                    self._returnTime(self.__EndTime, True), 
                    self._returnTime(t_high, True)))
            self.__EndTime = t_high 
        new_duration = self.__EndTime - self.__RefTime
        if verbose and old_duration != new_duration:
            Logger.info("New duration: {}"
                        .format(old_duration - new_duration))

        if new_duration < timedelta():
            ValueError("New duration {} is negative".format(new_duration))
        return (self.__RefTime, self.__EndTime)

    def GetStartTime(self, striso=False):
        """Return the start time of recording as it written in metadata.
        if striso set to True, returns an iso formated string"""
        return self._returnTime(self.__StartTime, striso)

    def GetStopTime(self, striso=False):
        """Return the stop time of recording as it written in metadata.
        if striso set to True, returns an iso formated string"""
        return self._returnTime(self.__StopTime, striso)

    def GetMaxTime(self, striso=False):
        """Return the time of first data point.
        if striso set to True, returns an iso formated string"""
        return self._returnTime(self.__MaxTime, striso)

    def GetMinTime(self, striso=False):
        """Return the time of last data point.
        if striso set to True, returns an iso formated string"""
        return self._returnTime(self.__MinTime, striso)

    def GetRefTime(self, striso=False):
        """Return reference start time.
        if striso set to True, returns an iso formated string"""
        return self._returnTime(self.__RefTime, striso)

    def GetEndTime(self, striso=False):
        """Return reference end time.
        if striso set to True, returns an iso formated string"""
        return self._returnTime(self.__EndTime, striso)

    def _returnTime(self, time, striso):
        if striso:
            if time:  
                return time.isoformat()
            else:
                return "None"
        else:
            return time

    def TimeIntersect(self, t_s1, t_e1, t_s2=None, t_e2=None):
        """
        returns intersection of time intervals [t_s1, t_e2) and
        [t_s2, t_e2).

        Parameters
        ----------
        t_s1: datetime
        t_e1: datetime
        t_s2: datetime, optional
        t_e2: datetime, optional

        Returns
        -------
        tupe(datetime, datetime)
        """
        if t_s2 is None: t_s2 = self.__RefTime
        if t_e2 is None: t_e2 = self.__EndTime
        ts = max(t_s1, t_s2)
        te = min(t_e1, t_e2)
        return (ts, te)

    ###########################
    # Subject and device info #
    ###########################

    def SetSubject(self, id="", name="", address="", gender="",
                   birth=datetime.min, notes="",
                   height=0, weight=0, head=0):
        self.SubjectInfo.ID = id
        self.SubjectInfo.Name = name
        self.SubjectInfo.Address = address
        self.SubjectInfo.Gender = gender
        self.SubjectInfo.Birth = birth
        self.SubjectInfo.Notes = notes
        self.SubjectInfo.Height = height
        self.SubjectInfo.Weight = weight
        self.SubjectInfo.Head = head

    def SetDevice(self, type="", id="", name="",
                  manufactor="", model="", version=""):
        self.DeviceInfo.Type = type
        self.DeviceInfo.ID = id
        self.DeviceInfo.Name = name
        self.DeviceInfo.Manufactor = manufactor
        self.DeviceInfo.Model = model
        self.DeviceInfo.Version = version

    ##############################
    # Task-description JSON file #
    ##############################

    def LoadJson(self, filename):
        """Loads JSOn file. If Given filename doesn't contain '.json'
        extension, a task name will be appended together with extension.
        """
        if not isinstance(filename,str):
            raise TypeError("filename must be a string")

        if filename[-5:] != ".json":
            filename += self.GetTask() + ".json" 
        filename = os.path.realpath(filename)
        Logger.info("JSON File: {}".format(filename))
        if not os.path.isfile(filename):
            raise FileNotFoundError("JSON file {} not found".format(filename))
        try:
            with open(filename) as f:
                self.JSONdata = json.load(f)
        except json.JSONDecodeError as ex:
            Logger.error("Unable to decode JSON file {}".format(filename))
            raise
        if "SamplingFrequency" in self.JSONdata:
            self.Frequency = self.JSONdata["SamplingFrequency"]
        if "TaskName" in self.JSONdata and \
                self.JSONdata["TaskName"] != self.GetTask():
            raise Exception(
                    "Task name '{}' in JSON file "
                    "mismach name in record '{}'"
                    .format(self.JSONdata["TaskName"],
                            self.GetTask()))

    def UpdateJSON(self):
        if not ("TaskName" in self.JSONdata):
            self.JSONdata["TaskName"] = self.GetTask()
        elif self.JSONdata["TaskName"] != self.GetTask():
            raise Exception("Task name in JSON file mismach task in Record")
        if "DeviceSerialNumber" not in self.JSONdata\
           and self.DeviceInfo.ID != "":
            self.JSONdata["DeviceSerialNumber"] = self.DeviceInfo.ID
        if "Manufacturer" not in self.JSONdata\
           and self.DeviceInfo.Manufactor != "":
            self.JSONdata["Manufacturer"] = self.DeviceInfo.Manufactor
        if "ManufacturersModelName" not in self.JSONdata\
                and self.DeviceInfo.Model != "":
            self.JSONdata["ManufacturersModelName"] = self.DeviceInfo.Model
        if "HeadCircumference" not in self.JSONdata\
                and self.SubjectInfo.Head > 0:
            self.JSONdata["HeadCircumference"] = self.SubjectInfo.Head
        self.JSONdata["SamplingFrequency"] = self.__Frequency
        if "RecordingDuration" not in self.JSONdata:
            self.JSONdata["RecordingDuration"] = round(
                    (self.__EndTime - self.__RefTime).total_seconds(),1)

        counter = {"EEGChannelCount":0, "EOGChannelCount":0, 
                   "ECGChannelCount":0, "EMGChannelCount":0, 
                   "MiscChannelCount":0}
        for ch in self.Channels:
            if "EEG" in ch.SigType:
                counter["EEGChannelCount"] += 1
            elif "EOG" in ch.SigType:
                counter["EOGChannelCount"] += 1
            elif "ECG" in ch.SigType or "EKG" in ch.SigType:
                counter["ECGChannelCount"] += 1
            elif "EMG" in ch.SigType:
                counter["EMGChannelCount"] += 1
            else:
                counter["MiscChannelCount"] += 1
        self.JSONdata.update(counter)

    def CheckJSON(self):
        diff = [k for k in JSONfields if k not in self.JSONdata]
        res1 = [k for k in diff if JSONfields[k] == 0]
        res2 = [k for k in diff if JSONfields[k] == 1]
        res3 = [k for k in diff if JSONfields[k] == 2]
        res4 = [k for k in self.JSONdata if k not in JSONfields]
        return (res1,res2,res3,res4)

    def DumpJSON(self):
        Logger.info("Creating eeg.json file")
        with open(self.Path(appdir="eeg",
                            appfile=self.GetPrefix() + "_eeg.json"),
                  'w', encoding='utf-8') as f:
            json.dump(self.JSONdata, f, 
                      skipkeys=False, indent="  ", 
                      separators=(',',':'))

    ##############################
    # Channels related functions #
    ##############################

    def ReadChannels(self, name=None,
                     white_list=[], black_list=[], 
                     bidsify=False):
        """
        reads and add channels from input folder.
        If white list is non empty, only channels with name in list 
        are concidered.
        If black list non empty, exclude channels with name in list.

        Parameters
        ----------
        name : str, optional
            name of channel to read, if None, all channels will be read
        white_list : list(str)
            list of channel names to concider
        black_list : list(str)
            list of channel names to ignore
        bidsify : bool
            set to True for force channel types to comply to BIDS
        """
        channels = self._readChannels(name)
        for c in channels:
            self.__addChannel(c,white_list, black_list)
        self.InitChannels(bidsify=bidsify)

    def _readChannels(self, name=None):
        """
        pure virtual function that read given channel form file.
        If name not defined, all available channels will be readed.

        Always raise NotImplementedError

        Parameters
        ----------
        name : str, optional
            name of channel to read, if not set, 
            reads all available channels

        Raises
        ------
        NotImplementedError
            if function is not overloaded for given class

        Returns
        -------
        list(GenChannel)
            the type of channel depends on implementation, but always inherits
            DataStructure.Generic.GenChannel
        """
        raise NotImplementedError

    def AddChannels(self, channels,
                    white_list=[], black_list=[],
                    bidsify=False):
        """
        add channel from list to record.  
        If white list is non empty, only channels with name in list 
        are concidered.
        If black list non empty, exclude channels with name in list.

        Parameters
        ----------
        channels : list(GenChannel)
            list of channels to add, must inherits from 
            DataStructure.Generic.GenChannel
        channels : GenChannel
            channel to add, must inherits from 
            DataStructure.Generic.GenChannel
        white_list : list(str)
            list of channel names to concider
        black_list : list(str)
            list of channel names to ignore
        bidsify : bool
            set to True for force channel types to comply to BIDS
        """
        if isinstance(channels, list):
            for c in channels:
                self.__addChannel(c,white_list, black_list)
        else:
            self.__addChannel(channels, white_list, black_list)
        self.InitChannels(bidsify=bidsify)

    def __addChannel(self, c, white_list=[], black_list=[]):
        if not isinstance(c, Channel):
            raise TypeError("Variable {} is not of a channel type".format(c))
        if black_list != [] and (c.GetName() in black_list): 
            self._dropped.append(c.GetName())
            return False
        if white_list == [] or (c.GetName() in white_list):
            self.Channels.append(c)
            Logger.debug("Channel {}, type {}, Sampling {} Hz".format(
                c.GetName(), c.GetId(), int(c.GetFrequency())))
            return True
        else:
            self._dropped.append(c.GetName())
            return False

    def SetMainChannel(self, chan_name=""):
        if not isinstance(chan_name, str):
            raise TypeError("chan_name must be a string")
        self._mainChannel = None
        if chan_name != "":
            for c in self.Channels:
                if c.GetName() == chan_name:
                    self._mainChannel = c
                    Logger.debug('Found main channel {}, type {}'.format(
                        c.GetName(), c.GetId()))
                    break
            if not self._mainChannel:
                Logger.warning("Unable find main channel " + chan_name)
        return self._mainChannel

    def GetMainChannel(self):
        return self._mainChannel

    def InitChannels(self, resetFrequency=False, bidsify=False):
        """Sort, rebuild and updates dictionary, frequency and min/max times"""
        # Sorting by Id
        self.Channels.sort()
        # Rebuilding dictionary and min/max time
        self._chDict = dict()
        self.__MinTime = datetime.max
        self.__MaxTime = datetime.min
        if resetFrequency:
            self.__Frequency = 1
        for c in self.Channels:
            if c in self._chDict:
                Logger.warning("Channel {} has same Id {} as channel {}"
                               .format(c.GetName(), c.GetId(),
                                       self._chDict[c.GetId()].GetName())
                               )
            else:
                self._chDict[c.GetId()] = c
            if c.GetSequenceStart(0) < self.__MinTime:
                self.__MinTime = c.GetSequenceStart(0)
                Logger.debug('Updated min time to {} from {}'.format(
                    self.__MinTime.isoformat(), c.GetName()))
            if c.GetSequenceEnd(-1) > self.__MaxTime:
                self.__MaxTime = c.GetSequenceEnd(-1)
                Logger.debug('Updated max time to {} from {}'.format(
                    self.__MaxTime.isoformat(), c.GetName()))
            if c.GetFrequency() != self.__Frequency:
                Logger.debug("Channel '{}': "
                             "Mismatch common sampling frequency {} Hz"
                             .format(c.GetName(), self.__Frequency))
                fr = self.__Frequency
                self.AddFrequency(c.GetFrequency())
                if fr != self.__Frequency:
                        Logger.info("Updated common sampling frequency "
                                    "to {} Hz".format(self.__Frequency))
            if bidsify:
                c.BidsifyType()

    def GetChannelById(self, Id):
        if Id in self._chDict:
            return self._chDict[Id]
        else:
            raise KeyError("Id {} not in the list of channels")

    ###########################
    # Event related functions #
    ###########################

    def ReadEvents(self, white_list=[], black_list=[]):
        """
        reads and add events from input
        If white list is non empty, only events with name in list 
        are concidered.
        If black list non empty, exclude events with name in list.

        Parameters
        ----------
        white_list : list(str)
            list of events names to concider
        black_list : list(str)
            list of events names to ignore
        """
        self.AddEvents(self._readEvents(), white_list, black_list)

    def _readEvents(self):
        raise NotImplemented

    def AddEvents(self, events, white_list=[], black_list=[]):
        if isinstance(events, list):
            for ev in events:
                self.__addEvent(ev, white_list, black_list)
        else:
            self.__addEvent(events, white_list, black_list)

    def __addEvent(self, ev, white_list=[], black_list=[]):
        if not isinstance(ev, Event):
            raise TypeError("Variable {} is not of a event type".format(ev))
        if black_list != [] and ev.GetName() in black_list:
            return
        if white_list == [] or (ev.GetName() in white_list):
            c_list = [c_id for c_id in ev.GetChannels()
                      if c_id in self._chDict]
            c_drop = [c_id for c_id in ev.GetChannels()
                      if c_id in self._dropped]
            if c_list != []:
                ev.RemoveChannel()
                ev.AddChannel(c_list)
            elif c_drop == []:
                Logger.warning("In Event {}, channels {} are "
                               "not in the list of channels"
                               .format(ev.GetName(), ev.GetChannels()))
                return
            if ev not in self.Events:
                bisect.insort(self.Events, ev)
                Logger.debug("Event {}, at {}".format(
                    ev.GetName(), ev.GetTime().isoformat()))
            else:
                self.Events[self.Events.index(ev)].AddChannel(ev.GetChannels())

    def EventsInTime(self, t_low=None, t_high=None):
        if t_low == datetime.min or t_low == datetime.max: t_low = None
        if t_high == datetime.min or t_high == datetime.max: t_high = None

        if not t_low : t_low = self.__RefTime
        if not t_high: t_high = self.__EndTime

        return [ev for ev in self.Events
                if (ev.GetTime() >= t_low and ev.GetTime() <= t_high)]

    def SearchEvent(self, event, pos=0, MinTime=None):
        """
        search and return index to the first event of given name after
        (inclusive) position start and after time MinTime

        Parameters
        ----------
        event : str
            name for event to search
        pos : int
            starting position for searching
        MinTime : datetime, optional
            if set, ignore events before this time

        Returns
        -------
        int
            index of found event
        None
            if event not found, or pos out of events range

        Raises
        ------
        TypeError
            if parameters are of wrong type
        """
        if not isinstance(event, str):
            raise TypeError("event mus be a string")
        if not isinstance(pos, int):
            raise TypeError("pos must be an int")
        if MinTime is not None and not isinstance(MinTime, datetime):
            raise TypeError("minTime must be a datetime")
        if pos < 0 : pos += len(self.Events)
        if pos < 0 or pos >= len(self.Events) : return None

        for i in range(pos, len(self.Events)):
            if MinTime is not None:
                if self.Events[i].GetTime() < MinTime:
                    continue
            if self.Events[i].Getname() == event:
                return i

        return None

    def RSearchEvent(self, event, pos=-1, MinTime=None):
        """
        reverse search and return index to the last event of given name
        before (inclusive) position start and before time MaxTime

        Parameters
        ----------
        event : str
            name for event to search
        pos : int
            starting position for searching
        MinTime : datetime, optional
            if set, ignore events before this time

        Returns
        -------
        int
            index of found event
        None
            if event not found, or pos out of events range

        Raises
        ------
        TypeError
            if parameters are of wrong type
        """
        if not isinstance(event, str):
            raise TypeError("event mus be a string")
        if not isinstance(pos, int):
            raise TypeError("pos must be an int")
        if MinTime is not None and not isinstance(MinTime, datetime):
            raise TypeError("minTime must be a datetime")
        if pos < 0 : pos += len(self.Events)
        if pos < 0 or pos >= len(self.Events) : return None

        for i in range(pos, -1, -1):
            if MinTime is not None:
                if self.Events[i].GetTime() > MinTime:
                    continue
            if self.Events[i].Getname() == event:
                return i

        return None

    def SearchEventByTime(self, MinTime):
        """
        search and returns index to the first event after given time
        returns None if not found

        Parameters
        ----------
        MinTime : datetime
            time from which serarch for event

        Returns
        -------
        int
            index to the first event after MinTime

        Raises
        ------
        TypeError
            if parameters are of uncorrect type
        """
        if MinTime is not None and not isinstance(MinTime, datetime):
            raise TypeError("MinTime must be a datetime")
        for i, ev in enumerate(self.Events):
            if ev.GetTime() >= MinTime: return i
        return None

    def RSearchEventByTime(self, MaxTime):
        """
        reverse search and returns index to the last event before 
        given time. Returns None if not found

        Parameters
        ----------
        MaxTime : datetime
            time to which serarch for event

        Returns
        -------
        int
            index to the last event before MaxTime

        Raises
        ------
        TypeError
            if parameters are of uncorrect type
        """
        if MaxTime is not None and not isinstance(MaxTime, datetime):
            raise TypeError("MaxTime must be a datetime")
        for i, ev in enumerate(self.Events):
            if ev.GetTime() <= MaxTime: return i
        return None

    def GetRuns(self, openingEvents=[], closingEvents=[], min_span=0):
        res = []
        # Getting runs by main channel
        if openingEvents == [] and closingEvents == []:
            if self._mainChannel is None:
                raise Exception("Main channel not defined")
            for i in range(0, self._mainChannelGetNsequences()):
                span = self._mainChannel.GetSequenceDuration(i)
                if span > min_span:
                    ts, te = self.TimeIntersect(
                            self._mainChannel.GetSequenceStart(i), 
                            self._mainChannel.GetSequenceStart(i)
                            + timedelta(seconds=span))
                    if te > ts:
                        res.append([ts,te])
        # Getting runs by event and span
        if openingEvents != [] and closingEvents == []:
            for opEv in openingEvents:
                for ev in self.Events:
                    if ev.GetName() == opEv:
                        span = ev.GetDuration() + 1
                        if span > min_span:
                            ts, te = self.TimeIntersect(
                                    ev.GetTime(), 
                                    ev.GetTime()
                                    + timedelta(seconds=span))
                            if te > ts:
                                res.append([ts,te])
        # Getting by opening and closing events
        if openingEvents != [] and closingEvents != []:
            for opEv,clEv in zip(openingEvents, closingEvents):
                l_t = None
                r_t = None
                l_c = 0
                for ev in self.Events:
                    if ev.GetName() == opEv and l_c == 0:
                        l_t = ev.GetTime()
                        l_c = 1
                    elif ev.GetName() == clEv:
                        if l_c == 0:
                            Logger.warning("Extra closing event {} at {}"
                                           .format(clEv, ev.GetTime()))
                            break
                        l_c -= 1
                        if l_c == 0:
                            r_t = ev.GetTime()
                            if (r_t - l_t).total_seconds() < min_span:
                                continue
                            l_t, r_t = self.TimeIntersect(l_t, r_t)
                            if l_t < r_t:
                                res.append([l_t,r_t])
                    elif ev.GetName() == opEv:
                        l_c += 1
                if l_c != 0:
                    Logger.warning("Unclosed event {} at {}".format(opEv, l_t))
        return res

    ##############################
    # Metadata related functions #
    ##############################
    def LoadMetadata(self):
        """
        loads metadata from imput files and performs preliminary checks. 
        Input path must be defined

        Raises
        ------
        ValueError
            if input path is not defined
        FileNotFoundError
            if one of manadatory files not found
        """
        if self.GetInputPath() is None:
            raise ValueError("Input path is not defined")
        self._loadMetadata()

    def _loadMetadata(self):
        """
        pure virtual function that loads metadata from imput files 
        and performs preliminary checks.

        Always raises NotImplementedError

        Raises
        ------
        NotImplementedError
        """
        raise NotImplementedError
