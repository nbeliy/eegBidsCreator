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
            "Frequency",
            "__path", "__prefix"]
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
        self.Frequency      = 1

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

