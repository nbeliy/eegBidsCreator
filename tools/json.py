import os
import json
import logging
import re
import datetime

Logger = logging.getLogger(__name__)

"""Module with functions treating all JSON related staff"""


def loadJson(filename, app=""):
    """Reads JSON file and returns the resulting json object
    If given filename do not ends with '.json', forms new
    filename as follows: 'filename''app'.json
    """
    if not isinstance(filename,str):
        raise TypeError("filename must be a string")
    if not isinstance(app,str):
        raise TypeError("app must be a string")

    if filename[-5:] != ".json":
        filename += app + ".json" 
    filename = os.path.realpath(filename)
    Logger.info("JSON File: {}".format(filename))
    if not os.path.isfile(filename):
        raise FileNotFoundError("JSON file {} not found".format(filename))
    try:
        with open(filename) as f:
            return json.load(f)
    except json.JSONDecodeError as ex:
        Logger.error("Unable to decode JSON file {}".format(filename))
        raise


def eventsJson(filename):
    """Writes events.json file describing the events.tsv
    file fields."""
    Logger.info("Creating events.json file")
    ev_struct = {
                "responce_time" : {
                    "Description": "Response time measured in seconds. "
                                   "A negative response time can be used "
                                   "to represent preemptive responses "
                                   "and “n/a” denotes a missed response.",
                    "Units": "second"},
                "value"         : {
                    "Description": "The event TTL trigger value "
                                   "(EEG Marker value) associated "
                                   "with an event "},
                "channels"      : {
                    "Description": "Comma separated list of channels "
                                   "triggering an event"
                    }
                }
    return dumpJson(filename, ev_struct)


def participantsJson(filename):
    """Writes participants.json file describing the participants.tsv
    file fields."""
    Logger.info("Creating participantss.json file")
    part_struct = {
                    "age": {
                        "LongName"    : "Age",
                        "Description" : "Age of a subject",
                        "Units"       : "year"},
                    "sex": {
                        "LongName"    : "Sex",
                        "Description" : "Sex of a subject",
                        "Levels"      : {
                            "n/a" : "Not available",
                            "F"   : "Female",
                            "M"   : "Male"}
                          }
                    }
    return dumpJson(filename, part_struct)


def dumpJson(filename, data):
    """Writes a dictionary in data into json file"""
    if not isinstance(filename, str):
        raise TypeError("filename must be a string")
    if filename[-5:] != ".json":
        raise Exception("filename must end with '.json'")
    if os.path.isfile(filename):
        Logger.warning("JSON file {} already exists. It will be replaced."
                       .format(filename))
    if not isinstance(data, dict):
        raise TypeError("data must be a dictionary")

    with open(filename, 'w') as f:
            return json.dump(data, f, indent="  ", separators=(',',':'))


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


class fieldLibrary(object):
    """
    a library class for fields.

    An instance of this class is meant to be declared static for each 
    type (events, channels, subjects, scans etc.). Then suggested and
    custom fields are added and activated manually via AddField function.
    Each added field must have an unique name. 

    A dictionary with names of activated fields as keys and coressponding
    values as values need to be filled. Such dictionary, passed to 
    GetLine function will return tab-separated line with values interpreted
    via str(), empty values ('' or None) will be replaced as 'n/a'
    """
    __slots__ = ["__library", "__nactive"]

    def __init__(self):
        """
        creator
        """
        self.__library = list()
        self.__nactive = 0

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
            if fe.Active():
                self.__nactive += 1
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
        old = self.__library[name].__activated 
        if old == act : return
        if act:
            self.__nactive += 1
        else:
            self.__nactive -= 1
        self.__library[name].__activated = act

    def GetNActive(self):
        """
        returns number of active files
        """
        return self.__nactive

    def GetActive(self):
        """
        returns a list of active field names
        """
        active = [f.GetName() for f in self.__library if f.Active()]
        if len(active) != self.GetNActive():
            raise ValueError("number of active fields mismutch number "
                             "of fields in header")
        return active

    def GetHeader(self):
        """
        returns tab-separated string with names of activated
        fields. string does not contain new line.

        Returns
        -------
        str
            header line

        Raises
        ------
        ValueError
            if number of active fields mismutch number of fields in 
            header
        """
        line = [f.GetName() for f in self.__library if f.Active()]
        if len(line) != self.GetNActive():
            raise ValueError("number of active fields mismutch number "
                             "of fields in header")
        return ('\t'.join(line))

    def GetLine(self, values):
        """
        returns tab-separated string with values corresponding 
        to active field. All values are normalized, i.e. converted 
        to string and '\t', '\n' are replaced by ' '. Empty strings 
        are replaced by 'n/a'. 

        List values are put in form '[v1, v2, v3]'.

        output string does not ends with new line

        Parameters
        ----------
        values : dict
            a dictionary of values with keys corresponding to fields 
            defined in library

        Returns
        -------
        str
            tab-separated string formatted folowing BIDS
            https://bids-specification.readthedocs.io/en/\
latest/02-common-principles.html

        """ 
        active = self.GetActive() 
        result = list()
        for f in active:
            if f in values:
                result.append(self.Normalize(values[f]))
            else:
                result.append('n/a')
        return "\t".join(result)

    @classmethod
    def Normalize(cls, value):
        """
        class method

        returns string folowwing BIDS:
        the datetime objects are printed in isoformat
        timedelta printed as seconds
        "" and None replaced by 'n/a'
        '\t', '\n' replaced by ' '

        Returns
        -------
        str
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
        dump fields definitions to a json file
        """
        struct = dict()

        for f in self.__library:
            if f.Active():
                struct[f.GetName()] = f.GetValues()

        return dumpJson(filename, struct)
