from datetime import datetime
import glob, os
import logging
import bisect

from DataStructure.Generic.Channel import GenChannel as Channel
from DataStructure.Generic.Event   import GenEvent   as Event

Logger = logging.getLogger(__name__)

class Subject(object):
    __slots__ = ["ID", "Name", "Address", "__gender", "Birth", "Notes", "Height", "Weight", "Head"]
    def __init__(self):
        self.ID   = ""
        self.Name = ""
        self.Address = ""
        self.Gender  = 0
        self.Birth   = datetime.min
        self.Notes   = ""
        self.Height  = 0
        self.Weight  = 0
        self.Head    = 0

    @property
    def Gender(self):
        return self.__gender
    @Gender.setter
    def Gender(self, value):
        if value == None:
            self.__gender = 0
            return
        if isinstance(value, str):
            if value in ["H","h", "M", "m"]:
                self.__gender = 2
                return
            if value in ["F", "f", "W", "w"]:
                self.__gender = 1
                return
            raise ValueError("Unknown Gender identification: "+value)
        if isinstance(value, int):
            if value in [0,1,2]:
                self.__gender = value
                return
            raise ValueError("Unknown Gender identification: "+value)
        raise ValueError("Gender identification must be integer or string")
    

class Device(object):
    __slots__ = ["Type", "ID", "Name", "Manufactor", "Model", "Version"]
    def __init__(self):
        self.Type = ""
        self.ID   = ""
        self.Name = ""
        self.Manufactor = ""
        self.Model= ""
        self.Version = ""

class Record(object):
    __slots__ = ["JSONdata", "SubjectInfo", "DeviceInfo", "Type", 
            "__StartTime", "__StopTime",#Time when registrement actually starts and stops
            "__MinTime", "__MaxTime", #Time where the first and last data point are taken
            "__RefTime", "__EndTime", #Time limits concidered for confertion
            "__task", "__acquisition", "__session",
            "Channels", "_chDict", "_dropped","_mainChannel",
            "Events",
            "__Frequency",
            "__path", "__prefix",
            "_aDate",
            "_extList",
            "_eegPath"
            ]
    #__JSONfields contains the full list of fields in JSON with a tags:
    #   0 - required
    #   1 - recommended
    #   2 - optional
    __JSONfields = {"TaskName": 0, "TaskDescription": 1, "Instructions":1,
        "CogAtlasID":1, "CogPOID":1, 
        "InstitutionName":1, "InstitutionAddress":1, "InstitutionalDepartementName":1,
        "DeviceSerialNumber":1,
        "HeadCircumference":1,
        "SamplingFrequency":0,
        "EEGChannelCount":0, "EOGChannelCount":1, "ECGChannelCount":1, "EMGChannelCount":1, "MiscChannelCount":2, "TriggerChannelCount":1,
        "EEGReference":0, "PowerLineFrequency":0, "EEGGround":1,
        "EEGPlacementScheme":1,
        "Manufacturer":1, "ManufacturersModelName":2, "CapManufacturer":1, "CapManufacturersModelName":2,
        "HardwareFilters":2, "SoftwareFilters":0, 
        "RecordingDuration":1, 
        "RecordingType":1, "EpochLenght":1,
        "SoftwareVersions":1,
        "SubjectArtefactDescription":2}

    def __init__(self, task="", session = "", acquisition = "", run = "", AnonymDate=None):
        self._eegPath = None
        self.JSONdata       = dict()
        self.SubjectInfo    = Subject()
        self.DeviceInfo     = Device()
        self.Type           = ""
        self.__StartTime      = None
        self.__StopTime       = None
        self.__MinTime      = None
        self.__MaxTime       = None
        self.__RefTime      = None
        self.__EndTime       = None
        self.SetId(session, task, acquisition)
        self.ResetPath()

        self.Channels       = list()
        self._mainChannel   = None
        self.Events         = list()
        self._chDict        = dict()
        self._dropped       = list()
        self.__Frequency    = 1
        self._aDate = AnonymDate

        self._extList       = []
        

    @property
    def eegPath(self):
        return self._eegPath


    def SetEEGPath(self, prepath='.'):
        if not isinstance(prepath, str): raise TypeError("prepath must be a string")
        if self._eegPath != None:
            Logger.warning("EEG path is locked")
            return self._eegPath
        if not os.path.exists(prepath): 
            raise FileNotFoundError("Pre-path {} don't exists.".format(prepath))
        self._eegPath = os.path.realpath(prepath+'/'+self.Path())+'/'
        return self._eegPath

    def GetAuxFiles(self, path="."):
        if not isinstance(path, str):
            raise TypeError("Path must be a string")
        return  [
                    os.path.basename(f) 
                    for f in glob.glob(path+"/*") 
                    if not os.path.splitext(f)[1] in self._extList 
                ]

    def GetMainFiles(self, path="."):
        if not isinstance(path, str):
            raise TypeError("Path must be a string")
        return  [
                    os.path.basename(f) 
                    for f in glob.glob(path+"/*") 
                    if os.path.splitext(f)[1] in self._extList 
                ]



    def SetId(self, session="", task="", acquisition=""):
        if self._eegPath != None:
            Logger.warning("Recording IDs are locked")
            return
        self.__session      = session
        self.__acquisition  = acquisition
        self.__task         = task
        self.ResetPrefix()
        self.ResetPath()

    def GetSession(self):
        return self.__session
    def GetTask(self):
        return self.__task
    def GetAcquisition(self):
        return self.__acquisition


    def Prefix(self, run="", app=""):
        if run == "":
            return self.__prefix+app
        else: 
            return self.__prefix+"_run-"+run+app

    def ResetPrefix(self):
        if not self._eegPath == None:
            Logger.warning("EEG path is locked")
            return
        prefix = "sub-"+self.SubjectInfo.ID
        if self.__session != "":
            prefix += "_ses-" + self.__session
        prefix = prefix + "_task-" + self.__task
        if self.__acquisition != "": 
            prefix = prefix + "_acq-" + self.__acquisition 
        self.__prefix = prefix
        return prefix

    def Path(self, app = "eeg"):
        return self.__path+"/"+app

    def ResetPath(self):
        if not self._eegPath == None:
            Logger.warning("EEG path is locked")
            return
        path = "sub-"+self.SubjectInfo.ID
        if self.__session != "": 
            path = path + "/ses-" + self.__session 
        self.__path = path
        return self.Path()

    @property
    def Frequency(self): return self.__Frequency
    @Frequency.setter
    def Frequency(self, value):
        if not isinstance(value, int):
            raise TypeError("Only integer frequency is supported")
        if value <= 0 :
            raise ValueError("Frequency must be positive non null value")
        self.__Frequency = value

    def AddFrequency(self, value):
        if not isinstance(value, int):
            raise TypeError("Only integer frequency is supported")
        if value <= 0 :
            raise ValueError("Frequency must be positive non null value")
        if self.__Frequency == 0 or value == self.__Frequency:
            self.__Frequency = value
            return
        lcd = min(self.__Frequency, value)
        while (lcd % value != 0) or (lcd % self.__Frequency != 0):
            lcd += 1
        self.__Frequency = lcd

    """Time-related functions"""
    def SetStartTime(self, t_start = None, t_end = None):
        """Sets recording start/end times to given values.
        Returns resulting times in tuple"""
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
        self.__StopTime   = t_end
        return (self.__StartTime, self.__StopTime)

    def SetReferenceTime(self, t_ref = None, t_end = None):
        """Setes the reference times to given values.
        If no values given, set to (in oreder):
        recording time, or main channel times, or min/max times
        """ 
        if t_ref == datetime.min or t_ref == datetime.max: t_ref = None
        if t_end == datetime.min or t_end == datetime.max: t_end = None
            
        if t_ref:
            self.__RefTime = t_ref
        elif self.__StartTime:
            self.__RefTime = self.__StartTime
        elif self._mainChannel:
            self.__RefTime = self._mainChannel.GetSequenceStart(0)
        else:
            self.__RefTime = self.__MinTime
        if t_end:
            self.__EndTime = t_end
        elif self.__StopTime:
            self.__EndTime = self.__StopTime
        elif self._mainChannel:
            self.__EndTime = self._mainChannel.GetSequenceEnd(-1)
        else:
            self.__EndTime = self.__MinTime
        return (self.__RefTime, self.__EndTime)

    def CropTime(self, t_low = None, t_high = None):
        """Crops the reference time to given values.
        if values are None or outside of actual reference times,
        no cropping is performed. To enlarge reference interval
        use SetReferenceTime"""
        if t_low == datetime.min or t_low == datetime.max: t_low = None
        if t_high == datetime.min or t_high == datetime.max: t_high = None
        
        if t_low and t_low < self.__RefTime: t_low = self.__RefTime
        if t_high and t_high > self.__EndTime: t_high = self.__EndTime

        if t_high != self.__EndTime or t_low != self.__RefTime:
            self.SetReferenceTime(t_low, t_high)
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

    def SetSubject(self, id = "", name = "", address = "", gender = "", birth = datetime.min, notes = "", height = 0, weight = 0, head = 0):
        self.SubjectInfo.ID   = id
        self.SubjectInfo.Name = name
        self.SubjectInfo.Address = address
        self.SubjectInfo.Gender  = gender
        self.SubjectInfo.Birth   = birth
        self.SubjectInfo.Notes   = notes
        self.SubjectInfo.Height  = height
        self.SubjectInfo.Weight  = weight
        self.SubjectInfo.Head    = head

    def SetDevice(self, type = "", id = "", name = "", manufactor = "", model = "", version = ""):
        self.DeviceInfo.Type = type
        self.DeviceInfo.ID   = id
        self.DeviceInfo.Name = name
        self.DeviceInfo.Manufactor = manufactor
        self.DeviceInfo.Model= model
        self.DeviceInfo.Version = version

    def UpdateJSON(self):
        if not ("TaskName" in self.JSONdata):
            self.JSONdata["TaskName"] = self.__task
        elif self.JSONdata["TaskName"] != self.__task:
            raise Exception("Task name in JSON file mismach task in Record")
        if not ("DeviceSerialNumber" in self.JSONdata) and self.DeviceInfo.ID != "":
            self.JSONdata["DeviceSerialNumber"] = self.DeviceInfo.ID
        if not ("Manufacturer" in self.JSONdata) and self.DeviceInfo.Manufactor != "":
            self.JSONdata["Manufacturer"] = self.DeviceInfo.Manufactor
        if not ("ManufacturersModelName" in self.JSONdata) and self.DeviceInfo.Model != "":
            self.JSONdata["ManufacturersModelName"] = self.DeviceInfo.Model
        if not ("HeadCircumference" in self.JSONdata) and self.SubjectInfo.Head > 0:
            self.JSONdata["HeadCircumference"] = self.SubjectInfo.Head
        self.JSONdata["SamplingFrequency"] = self.__Frequency
        if not ("RecordingDuration" in self.JSONdata):
            self.JSONdata["RecordingDuration"] = round((self.__EndTime - self.__RefTime).total_seconds(),1)
        counter = {"EEGChannelCount":0, "EOGChannelCount":0, 
                    "ECGChannelCount":0, "EMGChannelCount":0, 
                    "MiscChannelCount":0}
        for ch in self.Channels:
            if   "EEG" in ch.SigType: counter["EEGChannelCount"] += 1
            elif "EOG" in ch.SigType: counter["EOGChannelCount"] += 1
            elif "ECG" in ch.SigType or "EKG" in ch.SigType : counter["ECGChannelCount"] += 1
            elif "EMG" in ch.SigType: counter["EMGChannelCount"] += 1
            else: counter["MiscChannelCount"] += 1
        self.JSONdata.update(counter)

    def CheckJSON(self):
        diff = [ k for k in self.__JSONfields if k not in self.JSONdata ]
        res1 = [k for k in diff if self.__JSONfields[k] == 0 ]
        res2 = [k for k in diff if self.__JSONfields[k] == 1 ]
        res3 = [k for k in diff if self.__JSONfields[k] == 2 ]
        res4 = [ k for k in self.JSONdata if k not in self.__JSONfields ]
        return (res1,res2,res3,res4)
            

    """Channels related functions"""
    def AddChannels(self, channels, white_list=[], black_list=[] ):
        if isinstance(channels, list):
            for c in channels:
                self.__addChannel(c,white_list, black_list)
        else:
            self.__addChannel(channels, white_list, black_list)
        self.InitChannels()
        
    def __addChannel(self, c, white_list=[], black_list=[]):
        if not isinstance(c, Channel):
            raise TypeError("Variable {} is not of a channel type".format(c))
        if black_list != [] and (c.GetName() in black_list): 
            self._dropped.append(c.GetName())
            return
        if white_list == [] or ( c.GetName() in  white_list ):
            self.Channels.append(c)
            Logger.debug("Channel {}, type {}, Sampling {} Hz".format(
                c.GetName(), c.GetId(), int(c.GetFrequency())))
        else:
            self._dropped.append(c.GetName())

    def SetMainChannel(self, chan_name = ""):
        if not isinstance(chan_name, str):
            raise TypeError("Chan_name must be a string")
        self._mainChannel = None
        if chan_name != "":
            for c in self.Channels:
                if c.GetName() == chan_name:
                    self._mainChannel = c
                    Logger.debug('Found main channel {}, type {}'.format(
                        c.GetName(), c.GetId()))
                    break
            if not self._mainChannel:
                Logger.warning("Unable find main channel "+chan_name)
        return self._mainChannel
    def GetMainChannel(self):
        return self._mainChannel


    def InitChannels(self, resetFrequency=False):
        """Sort, rebuild and updates dictionary, frequency and min/max times"""
        #Sorting by Id
        self.Channels.sort()
        #Rebuilding dictionary and min/max time
        self._chDict =  dict()
        self.__MinTime = datetime.max
        self.__MaxTime = datetime.min
        if resetFrequency:
            self.__Frequency = 1
        for c in self.Channels:
            if c in self._chDict:
                Logger.warning("Channel {} has same Id {} as channel {}".format(
                        c.GetName(), c.GetId(), self._chDict[c.GetId()].GetName() ))
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
                Logger.debug("Channel '{}': Mismatch common sampling frequency {} Hz".format(
                        c.GetName(), self.__Frequency))
                fr = self.__Frequency
                self.AddFrequency(c.GetFrequency())
                if fr != self.__Frequency:
                        Logger.info("Updated common sampling frequency to {} Hz".format(self.__Frequency))


    """Event related functions"""
    #self.Events
    def AddEvents(self, events, white_list=[], black_list=[] ):
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
        if white_list == [] or (ev.GetName in  white_list):
            c_list = [c_id for c_id in ev.GetChannels() if c_id in self._chDict]
            c_drop = [c_id for c_id in ev.GetChannels() if c_id in self._dropped]
            if c_list != []:
                ev.RemoveChannel()
                ev.AddChannel(c_list)
            elif c_drop == []:
                Logger.warning("In Event {}, channels {} are not in the list of channels".format(ev.GetName(), ev.GetChannels()))
                return
            if not ev in self.Events:
                bisect.insort(self.Events, ev)
                Logger.debug("Event {}, at {}".format(
                    ev.GetName(), ev.GetTime().isoformat()))
            else:
                self.Events[self.Events.index(ev)].AddChannel(ev.GetChannels())

    def EventsInTime(self, t_low = None, t_high = None):
        if t_low == datetime.min or t_low == datetime.max: t_low = None
        if t_high == datetime.min or t_high == datetime.max: t_high = None

        if not t_low : t_low = self.__RefTime
        if not t_high: t_high = self.__EndTime

        return [ev for ev in self.Events if (ev.GetTime() >= t_low and ev.GetTime() <= t_high )]

    def GetRuns(self, openingEvents=[], closingEvents=[], min_span = 0):
        res = []
        #Getting runs by main channel
        if openingEvents==[] and closingEvents==[]:
            if self._mainChannel == None:
                raise Exception("Main channel not defined")
            for i in range(0, self._mainChannelGetNsequences()):
                span = self._mainChannel.GetSequenceDuration(i)
                if span > min_span:
                    ts, te = self.TimeIntersect(self._mainChannel.GetSequenceStart(i), 
                                self._mainChannel.GetSequenceStart(i) + timedelta(seconds=span))
                    if te > ts:
                        res.append([ts,te])
        #Getting runs by event and span
        if openingEvents!=[] and closingEvents==[]:
            for opEv in openingEvents:
                for ev in self.Events:
                    if ev.GetName() == opEv:
                        span = ev.GetDuration()+1
                        if span > min_span:
                            ts, te = self.TimeIntersect(ev.GetTime(), ev.GetTime() + timedelta(seconds=span))
                            if te > ts:
                                res.append([ts,te])
        #Getting by opening and closing events
        if openingEvents!=[] and closingEvents!=[]:
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
                            Logger.warning("Extra closing event {} at {}".format(clEv, ev.GetTime()))
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

    def TimeIntersect(self, t_s1, t_e1, t_s2 = None, t_e2 = None):
        if t_s2 == None: t_s2 = self.__RefTime
        if t_e2 == None: t_e2 = self.__EndTime
        ts = max(t_s1, t_s2)
        te = min(t_e1, t_e2)
        return (ts, te)

