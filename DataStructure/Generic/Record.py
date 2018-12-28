from datetime import datetime

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
    __slots__ = ["JSONdata", "SubjectInfo", "DeviceInfo", "Type", "__StartTime", "__StopTime", 
            "__task", "__acquisition", "__session", "__run", 
            "Channels",
            "Events",
            "__Frequency",
            "__path", "__prefix"
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

    def __init__(self, task, session = "", acquisition = "", run = ""):
        self.JSONdata       = dict()
        self.SubjectInfo    = Subject()
        self.DeviceInfo     = Device()
        self.Type           = ""
        self.__StartTime      = datetime.min
        self.__StopTime       = datetime.min
        self.__task           = task
        self.__session        = session
        self.__acquisition    = acquisition
        self.__run            = run
        self.ResetPrefix()
        self.ResetPath()

        self.Channels       = []
        self.Events         = []
        self.__Frequency    = 1

    def Prefix(self):
        return self.__prefix

    def ResetPrefix(self):
        prefix = "sub-"+self.SubjectInfo.ID
        if self.__session != "":
            prefix += "_ses-" + self.__session
        prefix = prefix + "_task-" + self.__task
        if self.__acquisition != "": 
            prefix = prefix + "_acq-" + self.__acquisition 
        if self.__run != "": 
            prefix = prefix + "_run-" + self.__run
        self.__prefix = prefix
        return prefix

    def Path(self):
        return self.__path

    def ResetPath(self):
        path = "sub-"+self.SubjectInfo.ID
        if self.__session != "": 
            path = path + "/ses-" + self.__session 
        path += "/eeg"
        self.__path = path
        return path
        
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

    @property
    def StartTime(self):
        return self.__StartTime
    @StartTime.setter
    def StartTime(self, value):
        if value == None : 
            self.__StartTime = datetime.min
            return
        if not isinstance(value, datetime):
            raise ValueError("StartTime must be datetime instance")
        self.__StartTime = value

    @property
    def StopTime(self):
        return self.__StopTime
    @StopTime.setter
    def StopTime(self, value):
        if value == None : 
            self.__StopTime = datetime.min
            return
        if not isinstance(value, datetime):
            raise ValueError("StopTime must be datetime instance")
        self.__StopTime = value

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
            self.JSONdata["RecordingDuration"] = (self.__StopTime - self.__StartTime).total_seconds()

    def CheckJSON(self):
        diff = [ k for k in self.__JSONfields if k not in self.JSONdata ]
        res1 = [k for k in diff if self.__JSONfields[k] == 0 ]
        res2 = [k for k in diff if self.__JSONfields[k] == 1 ]
        res3 = [k for k in diff if self.__JSONfields[k] == 2 ]
        res4 = [ k for k in self.JSONdata if k not in self.__JSONfields ]
        return (res1,res2,res3,res4)
            
