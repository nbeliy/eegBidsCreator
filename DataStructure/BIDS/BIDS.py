import os
import json
import logging
import re
import datetime

Logger = logging.getLogger(__name__)

"""
describes and governs all BIDS nessesary datas and structures
"""


class BIDSid(object):
    __slots__ = ["__subject", 
                 "__task", "__acquisition", "__session",
                 "__run",
                 "__innerPath",
                 "__locked"]

    def __init__(self, subject="",
                 session="", task="", acquisition="",
                 run=None):
        """
        constructor

        Raises
        ------
        TypeError
            if passing parameters of incorrect type
        """
        if not isinstance(session, str):
            raise TypeError("session must be a string")
        if not isinstance(task, str):
            raise TypeError("task must be a string")
        if not isinstance(acquisition, str):
            raise TypeError("acquisition must be a string")
        if run is not None and not isinstance(run, str):
            raise TypeError("run must be an int")
        self.__innerPath = None
        self.__locked = False
        self.SetId(subject, session, task, acquisition)
        self.SetRun(run)
        self.ResetPrefix()

    def SetId(self, subject=None, session=None,
              task=None, acquisition=None):
        """
        sets the identification of sample -- session, task and acquisition
        prefixes and paths will also be recalculated.

        If parameter is not set, then corresponding label will not be changed

        Parameters
        ----------
        subject: str, optional
            label uniquelly identifying a given subject
        session: str, optional
            logical grouping of neuroimaging and behavioral data consistent 
            across subjects
        task: str, optional
            a set of structured activities performed by the participant
        acquisition : str, optional
            a continuous uninterrupted block of time during which 
            a brain scanning instrument was acquiring data according 
            to particular scanning sequence/protocol
        run: int, optional
            an uninterrupted repetition of data acquisition that has 
            the same acquisition parameters and task (however events 
            can change from run to run due to different subject response 
            or randomized nature of the stimuli).

        Raises
        ------
        TypeError
            if passed parameter are of wrong type
        ValueError
            if record is locked 
        ValueError
            if labels contains forbidden characters
        """
        if self.__locked:
            raise ValueError("record is locked")
        std = re.compile("[0-9a-zA-Z]*", flags=re.ASCII)
        if subject is not None:
            if not isinstance(subject, str):
                raise TypeError("subject must be a string")
            if std.fullmatch(subject) is None:
                Logger.warning("subject label '{}' contains "
                               "illegal characters. "
                               "Dataset will not be BIDS coplient"
                               .format(subject))
        if session is not None:
            if not isinstance(session, str):
                raise TypeError("session must be a string")
            if std.fullmatch(session) is None:
                Logger.warning("session label '{}' contains "
                               "illegal characters"
                               "Dataset will not be BIDS coplient"
                               .format(subject))
        if task is not None:
            if not isinstance(task, str):
                raise TypeError("task must be a string")
            if std.fullmatch(task) is None:
                Logger.warning("task label '{}' contains "
                               "illegal characters"
                               "Dataset will not be BIDS coplient"
                               .format(subject))
        if acquisition is not None:
            if not isinstance(acquisition, str):
                raise TypeError("acquisition must be a string")
            if std.fullmatch(acquisition) is None:
                Logger.warning("acquisition label '{}' contains "
                               "illegal characters"
                               "Dataset will not be BIDS coplient"
                               .format(subject))
        if subject is not None: self.__subject = subject
        if acquisition is not None: self.__acquisition = acquisition
        if task is not None: self.__task = task
        if session is not None: self.__session = session
        self.ResetPrefix()

    def SetRun(self, run=None):
        """
        sets run number. Do not lock record. 
        Can be changed after record is locked. 
        To unset run, pass None as parameter

        Parameters
        ----------
        run: int, optional
            an uninterrupted repetition of data acquisition that has 
            the same acquisition parameters and task (however events 
            can change from run to run due to different subject response 
            or randomized nature of the stimuli).

        Raises
        ------
        TypeError
            if passing parameters of incorrect type
        """
        if run is not None:
            if not isinstance(run, int):
                raise TypeError("run must be an int")
        self.__run = run

    def UnsetRun(self):
        """
        explicetly unsets run
        """
        self.__run = None

    def GetSubject(self):
        """
        provides subject label
        """
        return self.__subject

    def GetSession(self):
        """
        provides session label
        """
        return self.__session

    def GetTask(self):
        """
        provides task label
        """
        return self.__task

    def GetAcquisition(self):
        """
        provides acquisition label
        """
        return self.__acquisition

    def GetRun(self):
        """
        provides run index
        """
        return self.__run

    def GetPrefix(self, run=None, app=""):
        """
        provides bids-formatted prefix from the dataset id:
        sub-<sunbId>_task-<taskId>[_ses-<sesid>][_run-<runId>]
        If app is specifies, appends its value to prefix

        Parameters
        ----------
        run: int, optional
            the id of the run, if not set, recording-defined is used
        appendix: str
            appendix for prefix, for example file extention

        Returns
        -------
        str
            bids-formatted prefix

        Raises
        ------
        TypeError
            if parameters have incorrect type
        """
        if run is not None:
            if not isinstance(run, int):
                raise TypeError("run must be a int")
            if run < 0:
                raise ValueError("run must be positive or 0")
        else:
            run = self.__run
        if not isinstance(app, str):
            raise TypeError("app must be a string")
        if run is None:
            return self.__prefix + app
        else: 
            return self.__prefix + "_run-" + str(run) + app

    def ResetPrefix(self):
        """
        updates bids-formatted prefix and sub-path. Need to be called
        after changings in record IDs

        Returns
        -------
        str
            updated prefix

        Raises
        ------
        ValueError
            if record is locked
        """
        path = ""
        if self.__locked:
            raise ValueError("record IDs is locked")
        sub = ""
        ses = ""
        if self.__subject != "":
            sub = "sub-" + self.__subject
        if self.__session != "": 
            ses = "ses-" + self.__session 
        self.__innerPath = os.path.join(sub, ses) + "/"

        prefix = sub
        if self.__session != "":
            prefix += "_" + ses
        if self.__task != "":
            prefix += "_task-" + self.__task
        if self.__acquisition != "": 
            prefix = prefix + "_acq-" + self.__acquisition 
        self.__prefix = prefix

        return self.__prefix

    def GetInnerPath(self):
        """
        provides inner path -- BIDS formatted path within dataset directory
        """
        return self.__innerPath

    def Lock(self):
        """
        Forbids any futher changes in IDs and paths.
        If output path not set, will raise AttributeError

        Raises
        ------
        AttributeError
            if output path is not set
        """
        if self.__innerPath == "":
            raise AttributeError("prefix wasn't set")
        if self.__subject == "":
            raise AttributeError("subject wasn't set")
        self.__locked = True
        Logger.info("ID locked. Inner directory is '{}'"
                    .format(self.__innerPath))

    def IsLocked(self):
        """
        checks if current recor is locked (i.e. its IDs are allowed to change)

        Returns
        -------
        bool
            the locked status
        """
        return self.__locked


# JSONfields contains the full list of fields in JSON with a tags:
#   0 - required
#   1 - recommended
#   2 - optional
REQUIRED = 0
RECOMMENDED = 1
OPTIONAL = 2
JSONfields = {"TaskName": REQUIRED,

              "InstitutionName":RECOMMENDED, 
              "InstitutionAddress":RECOMMENDED,
              "Manufacturer":RECOMMENDED, 
              "ManufacturersModelName":OPTIONAL,
              "SoftwareVersions":RECOMMENDED,
              "TaskDescription": RECOMMENDED, 
              "Instructions":RECOMMENDED,
              "CogAtlasID":RECOMMENDED, 
              "CogPOID":RECOMMENDED, 
              "DeviceSerialNumber":RECOMMENDED,

              "EEGReference":REQUIRED, 
              "SamplingFrequency":REQUIRED,
              "PowerLineFrequency":REQUIRED, 
              "SoftwareFilters":REQUIRED, 

              "CapManufacturer":RECOMMENDED, 
              "CapManufacturersModelName":OPTIONAL,
              "EEGChannelCount":REQUIRED, 
              "ECGChannelCount":RECOMMENDED, 
              "EMGChannelCount":RECOMMENDED,
              "EOGChannelCount":RECOMMENDED,
              "MiscChannelCount":OPTIONAL, 
              "TriggerChannelCount":RECOMMENDED,
              "RecordingDuration":RECOMMENDED, 
              "RecordingType":RECOMMENDED, 
              "EpochLenght":RECOMMENDED,
              "HeadCircumference":RECOMMENDED,
              "EEGPlacementScheme":RECOMMENDED,
              "EEGGround":RECOMMENDED,
              "HardwareFilters":OPTIONAL, 
              "SubjectArtefactDescription":OPTIONAL
              }
"""
full list of task-description fields with corresponding statuses.
See https://bids-specification.readthedocs.io/en/stable/\
04-modality-specific-files/03-electroencephalography.html for full 
description
"""


class fieldEntry(object):
    """
    object containing a dictionary defining a given field in BIDS
    formatted .tsv file. This dictionary will be written into
    corresponding json file.
    """
    __slots__ = ["__name", "__values", "__activated"]

    def __init__(self, name, longName="", description="",
                 levels={}, units="", url="", activate=True):
        """
        constructor

        Parameters
        ----------
        name : str
            an id of a field, must be non-empty and composed only of
            [0-9a-zA-Z_]
        longName : str
            long (unabbreviated) name of the column.
        description : str
            description of the column
        levels : dict
            For categorical variables: 
            a dictionary of possible values (keys) 
            and their descriptions (values).
        units : str
            measurement units. [<prefix symbol>] <unit symbol> format 
            following the SI standard is RECOMMENDED. See
            https://bids-specification.readthedocs.io/en/latest/\
                    99-appendices/05-units.html
        url : str
            URL pointing to a formal definition of this type of data 
            in an ontology available on the web
        activate : bool
            will be created field activated or not

        Raises
        ------
        TypeError
            if passed parameters of incorrect type
        ValueError
            if name is invalid (empty or contains forbidden character)
        """
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        if not isinstance(longName, str):
            raise TypeError("longName must be a string")
        if not isinstance(description, str):
            raise TypeError("description must be a string")
        if not isinstance(units, str):
            raise TypeError("units must be a string")
        if not isinstance(url, str):
            raise TypeError("url must be a string")
        if not isinstance(activate, bool):
            raise TypeError("activate must be a bool")
        if not isinstance(levels, dict):
            raise TypeError("levels must be a dictionary")
        m = re.fullmatch('\\w*', name)
        if name == "" or m is None:
            raise ValueError("name '{}' is invalid".format(name))

        self.__name = name
        self.__values = dict()

        if longName != "":
            self.__values["LongName"] = longName
        if description != "":
            self.__values["Description"] = description
        if len(levels) > 0:
            self.__values["Levels"] = levels
        if units != "":
            self.__values["Units"] = units
        if url != "":
            self.__values["TermURL"] = url
        self.__activated = activate

    def Active(self):
        """
        returns activated status
        """
        return self.__activated

    def GetName(self):
        return self.__name

    def GetValues(self):
        return self.__values

    def __eq__(self, other):
        """
        definition of equality (==) operator by the name of field
        """
        if not isinstance(other, fieldEntry):
            raise TypeError("comparaison must be between same type")
        return self.__name == other.__name


class BIDSfieldLibrary(object):
    """
    a library class for fields used in BIDS tsv files.

    In order to an object to use BIDS tsv fields, this object must 
    inherit from this class.

    It contains a static list of available fields, and a dynamic 
    dictionary of values for each of objects.

    A list of required and suggested fields must be added to library in 
    class definition (outside of __init__). User-defined fields can be 
    added in plugin at any point.

    Each field can be described by its id (name), explicit name, description,
    possible values and descriptive url. For more details, refer to BIDS 
    description there:
    https://bids-specification.readthedocs.io/\
en/latest/02-common-principles.html

    Each field can be activated or deactivated. Only acive fields will be
    reported in json and tsv filres.

    The descriptive json file is created by BIDSdumpJSON(filename)
    The header line is created by static method BIDSgetHeader()
    Data line for each instance is created by BIDSgetLine()
    """
    __slots__ = ["__library"]

    def __init__(self):
        """
        creator
        """
        self.__library = list()

    def AddField(self, name, longName="", description="", 
                 levels={}, units="", url="", activated=True):
        """
        append new field to library. The field name must be unique

        Parameters
        ----------
        name : str
            an id of a field, must be non-empty and composed only of
            [0-9a-zA-Z_]
        longName : str
            long (unabbreviated) name of the column.
        description : str
            description of the column
        levels : dict
            For categorical variables: 
            a dictionary of possible values (keys) 
            and their descriptions (values).
        units : str
            measurement units. [<prefix symbol>] <unit symbol> format 
            following the SI standard is RECOMMENDED. See
            https://bids-specification.readthedocs.io/en/latest/\
                    99-appendices/05-units.html
        url : str
            URL pointing to a formal definition of this type of data 
            in an ontology available on the web
        activate : bool
            will be created field activated or not

        Raises
        ------
        TypeError
            if passed parameters are of invalid type
        IndexError
            if name of field is already in dictionary
        """
        fe = fieldEntry(name, longName, description, 
                        levels, units, url, activated)
        if fe not in self.__library:
            self.__library.append(fe)
        else:
            raise IndexError("Field in library already contains " + name)

    def Activate(self, name, act=True):
        """
        change activated status of given field

        Parameters
        ----------
        name : str
            name of field to change status. Must exist in library
        act : bool
            status to set

        Raises
        ------
        TypeError
            if passed parameters are of incorrect type
        keyError
            if field not found in dictionary
        """
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        if not isinstance(act, bool):
            raise TypeError("act must be bool")
        self.__library[name].__activated = act

    def GetNActive(self):
        """
        returns number of active fields
        """
        count = 0
        for f in self.__library:
            if f.Active(): count += 1
        return count

    def GetActive(self):
        """
        returns a list of names of active fields
        """
        active = [f.GetName() for f in self.__library if f.Active()]
        return active

    def GetHeader(self):
        """
        returns tab-separated string with names of activated
        fields. string does not contain new line.

        Returns
        -------
        str
            header line
        """
        line = [f.GetName() for f in self.__library if f.Active()]
        return ('\t'.join(line))

    def GetLine(self, values):
        """
        returns tab-separated string with given values. Values
        are searched by keys corresponding to active fields and
        normalized by Normalize function. Returned string does
        not contains new line and is conforms to BIDS, described
        there: https://bids-specification.readthedocs.io/en/\
latest/02-common-principles.html

        Parameters
        ----------
        values : dict, optional
            a dictionary of values with keys corresponding to fields 
            defined in library

        Returns
        -------
        str
            tab-separated string
        """ 
        if not isinstance(values, dict):
            raise TypeError("values must be a dictionary")
        active = self.GetActive() 
        result = list()
        for f in active:
            if f in values:
                result.append(self.Normalize(values[f]))
            else:
                result.append('n/a')
        return "\t".join(result)

    @staticmethod
    def Normalize(value):
        """
        adapt input value to format acceptable by BIDS tsv
        file. By default it transforms value to string using str(),
        then  it changes tab (\\t) and new line (\\n) to space.
        datetime types are transformed using isoformat, and 
        timedelta are expressed in seconds. Non-defined values
        (None) and empty strings are replaced by 'n/a'.

        Returns
        -------
        str
            normalized string
        """

        if value is None:
            return "n/a"
        v = ""
        if isinstance(value, datetime.datetime)\
           or isinstance(value, datetime.date)\
           or isinstance(value, datetime.time):
            v = value.isoformat()
        elif isinstance(value, datetime.timedelta):
            v = str(value.total_seconds())
        else:
            v = str(value).replace('\t', " ").replace('\n', " ")
        if v == "" : return "n/a"
        return v

    def GetTemplate(self):
        """
        returns a template dictionary for values with active fields 
        as keys and None as values
        """
        res = dict()
        for f in self.__library:
            res[f.GetName()] = None
        return res

    def DumpDefinitions(self, filename):
        """
        dump fields definitions to a json file. If file exists, it 
        will be replaced.

        Parameters
        ----------
        filename: str
            name of file to dump library

        Raises
        ------
        TypeError
            if passed parameters are of incorrect type
        """
        if not isinstance(filename, str):
            raise TypeError("filename must be a string")
        if filename[-5:] != ".json":
            raise ValueError("filename must end with '.json'")
        if os.path.isfile(filename):
            Logger.warning("JSON file {} already exists. It will be replaced."
                           .format(filename))
        struct = dict()

        for f in self.__library:
            if f.Active():
                struct[f.GetName()] = f.GetValues()

        with open(filename, 'w') as f:
            json.dump(struct, f, indent="  ", separators=(',', ':'))
