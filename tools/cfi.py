import configparser
import logging
from datetime import datetime

Logger = logging.getLogger(__name__)

'''
    Contain initialisation and default configuration file parameters
'''


def default_parameters():
    '''Creates and returns configparser.ConfigParser object 
    containing default configuration'''
    parameters = configparser.ConfigParser()
    # Making keys case-sensitive
    parameters.optionxform = lambda option: option
    # Setting up default values
    parameters['GENERAL'] = {
                            "PatientId"     :"",
                            "SessionId"     :"", 
                            "TaskId"        :"", 
                            "AcquisitionId" :"",
                            "RunId"         :"",
                            "JsonFile"      :"", 
                            "OutputFolder"  :".", 
                            "OverideDuplicated" : "yes",
                            "Conversion"    :"",
                            "CopySource"    :"yes",
                            "MemoryUsage"   :"2"
                            }
    parameters['LOGGING'] = {
                            "LogLevel"  :"INFO", 
                            "LogFile"   :"",
                            "Quiet"     :"no"
                            }
    parameters['CHANNELS'] = {
                            'WhiteList'   :"",
                            'BlackList'   :"",
                            'MainChannel' :""
                            }
    parameters['EVENTS'] = {
                            'WhiteList'   :"",
                            'BlackList'   :"",
                            "IgnoreOutOfTimeEvents" :"yes",
                            "IncludeSegmentStart"   :"no",
                            "MergeCommonEvents"     :"yes"
                            }
    parameters['DATATREATMENT'] = {
                            "StartTime"     :"", "EndTime"  :"", 
                            "StartEvent"    :"", "EndEvent" :"",
                                  }
    parameters['RUNS'] = {
                            "SplitRuns"     :"",
                            "OpeningEvents" :"",
                            "ClosingEvents" :"",
                            "MinSpan"       :"0"
                         }
    parameters['ANONYMIZATION'] = {
                                    "Anonymize" :"yes",
                                    "StartDate" :"1973-3-01",
                                    "SubjName"  :"John Doe",
                                    "BirthDate" :""
                                    }
    parameters['BIDS'] = {
                            "IncludeAuxiliary" :"no",
                            "OriginalTypes"    :"no"
                         }
    parameters['PLUGINS'] = {
                                    "Plugin" : ""
                            }
    parameters['BRAINVISION'] = {
                                    "Encoding"  :"UTF-8", 
                                    "DataFormat":"IEEE_FLOAT_32", 
                                    "Endian"    :"Little"
                                }
    parameters['EDF'] = {
                        "DataRecordDuration"    :"10"
                        }
    parameters['MEEG'] = {}
    return parameters


def read_parameters(parameters, config_file):
    '''Reads updates the parameters with values from config_file'''
    if not isinstance(parameters, configparser.ConfigParser):
        raise TypeError("Parameters must be a ConfigParcer instance")
    readed = 0
    if config_file:
        if not isinstance(config_file, str):
            raise TypeError("Configuration file name is not a string")
        readed = parameters.read(config_file)
        if len(readed) == 0:
            raise FileNotFoundError("Unable to open file " + config_file)
    return readed


def check_configuration(parameters):
    '''Check if parameters are valid'''
    if not isinstance(parameters, configparser.ConfigParser):
        raise TypeError("Parameters must be a ConfigParcer instance")
    passed = True

    # GENERAL
    sec = "GENERAL"
    passed = passed and check_string(parameters, sec, "PatientId")
    passed = passed and check_string(parameters, sec, "SessionId")
    passed = passed and check_string(parameters, sec, "TaskId")
    passed = passed and check_string(parameters, sec, "AcquisitionId")
    passed = passed and check_int(parameters, sec, "RunId")
    passed = passed and check_string(parameters, sec, "JsonFile")
    passed = passed and check_string(parameters, sec, 
                                     "OutputFolder", empty=False)
    passed = passed and check_bool(parameters, sec, "OverideDuplicated")
    passed = passed and check_string(parameters, sec, "Conversion",
                                     ["","BV","EDF","MEEG"])
    passed = passed and check_bool(parameters, sec, "CopySource")
    passed = passed and check_int(parameters, sec, "MemoryUsage")

    # LOGGING
    sec = "LOGGING"
    passed = passed and check_string(
                parameters, sec, "LogLevel",
                ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    passed = passed and check_string(parameters, sec, "LogFile")
    passed = passed and check_bool(parameters, sec, "Quiet")

    # CHANNELS
    sec = "CHANNELS"
    passed = passed and check_string(parameters, sec, "WhiteList")
    passed = passed and check_string(parameters, sec, "BlackList")
    passed = passed and check_string(parameters, sec, "MainChannel")

    # EVENTS
    sec = "EVENTS"
    passed = passed and check_string(parameters, sec, "WhiteList")
    passed = passed and check_string(parameters, sec, "BlackList")
    passed = passed and check_bool(parameters, sec, "IgnoreOutOfTimeEvents")
    passed = passed and check_bool(parameters, sec, "IncludeSegmentStart")
    passed = passed and check_bool(parameters, sec, "MergeCommonEvents")

    # DATATREATMENT
    sec = "DATATREATMENT"
    passed = passed and check_time(parameters, sec, "StartTime", chop=6)
    passed = passed and check_time(parameters, sec, "EndTime", chop=6)
    passed = passed and check_string(parameters, sec, "StartEvent")
    passed = passed and check_string(parameters, sec, "EndEvent")

    # RUNS
    sec = "RUNS"
    passed = passed and check_string(
                parameters, sec, "SplitRuns",
                ["", "Channel", "EventSpan", "EventLimit"])
    passed = passed and check_string(parameters, sec, "OpeningEvents")
    passed = passed and check_string(parameters, sec, "ClosingEvents")
    passed = passed and check_int(parameters, sec, "MinSpan")

    # ANONYMIZATION
    sec = "ANONYMIZATION"
    passed = passed and check_bool(parameters, sec, "Anonymize")
    passed = passed and check_time(parameters, sec, "StartDate", chop=3)
    passed = passed and check_string(parameters, sec, "SubjName")
    passed = passed and check_time(parameters, sec, "BirthDate", chop=3)

    # BIDS
    sec = "BIDS"
    passed = passed and check_bool(parameters, sec, "IncludeAuxiliary")
    passed = passed and check_bool(parameters, sec, "OriginalTypes")

    # PLUGINS
    sec = "PLUGINS"
    passed = passed and check_string(parameters, sec, "Plugin")

    # BRAINVISION
    sec = "BRAINVISION"
    passed = passed and check_string(parameters, sec, 
                                     "Encoding", empty=False)
    passed = passed and check_string(parameters, sec, 
                                     "DataFormat", empty=False)
    passed = passed and check_string(parameters, sec, 
                                     "Endian", empty=False)

    # EDF
    sec = "EDF"
    passed = passed and check_int(parameters, sec, 
                                  "DataRecordDuration", empty=False)

    if not passed: 
        return False

    # The format and values of all parameters are correct.
    # Checking compatibility of them

    # MainChannel
    if parameters["CHANNELS"]["MainChannel"] == "":
        if parameters["EVENTS"].getboolean("IncludeSegmentStart"):
            print("EVENTS: IncludeSegmentStart is defined" 
                  + "but MainChannel is not")
            passed = False
        if parameters["RUNS"]["SplitRuns"] == "Channel":
            print("RUNS: Splitting by channel, "
                  + "but MainChannel is not defined")
            passed = False

    # Checking lists
    ch_WL = get_list(parameters, "CHANNELS", "WhiteList", " ")
    ch_BL = get_list(parameters, "CHANNELS", "BlackList", " ")
    ev_WL = get_list(parameters, "EVENTS", "WhiteList", " ")
    ev_BL = get_list(parameters, "EVENTS", "BlackList", " ")
    run_OE = get_list(parameters, "RUNS", "OpeningEvents", " ")
    run_CE = get_list(parameters, "RUNS", "ClosingEvents", " ")

    if len(ch_WL) != 0 and len(ch_BL) != 0:
        print("CHANNELS: Both WhiteList and BlackList are defined")
        passed = False

    if len(ev_WL) != 0 and len(ev_BL) != 0:
        print("EVENTS: Both WhiteList and BlackList are defined")
        passed = False

    if len(run_CE) != 0 and len(run_CE) != len(run_OE):
        print("RUNS: Dimension of OpeningEvents mismatch ClosingEvents")
        passed = False

    # SplitRuns
    if parameters["GENERAL"]["RunId"] != "" \
            and parameters["RUNS"]["SplitRuns"] != "":
        print("RUNS: Can't force run Id and require split runs at same time")
        passed = False

    if parameters["RUNS"]["SplitRuns"] == "EventSpan":
        if parameters["RUNS"]["OpeningEvents"] == "":
            print("RUNS: Splitting by event but Event is not defined")
            passed = False
    if parameters["RUNS"]["SplitRuns"] == "EventLimit":
        if len(run_CE) == 0 or len(run_OE) == 0:
            print("RUNS: Splitting by Opening and Closing events," 
                  + "but one of them is not defined") 
            passed = False

    return passed


def check_bool(parameters, section, name, empty=True):
    val = parameters.get(section, name, fallback=None)
    if val is None:
        print(section + ": " + name + " not found")
        return False
    if val == "":
        if empty:
            return True
        else:
            print(section + ": Invalid " + name + "value : empty string")
            return False
    try:
        parameters[section].getboolean(name)
    except ValueError:
        print(section + ": Invalid " + name + " value " + val)
        return False
    return True


def check_int(parameters, section, name, empty=True):
    val = parameters.get(section, name, fallback=None)
    if val is None:
        print(section + ": " + name + " not found")
        return False
    if val == "":
        if empty:
            return True
        else:
            print(section + ": Invalid " + name + "value : empty string")
            return False
    try:
        parameters[section].getint(name)
    except ValueError:
        print(section + ": Invalid " + name + " value " + val)
        return False
    return True


def check_float(parameters, section, name, empty=True):
    val = parameters.get(section, name, fallback=None)
    if val is None:
        print(section + ": " + name + " not found")
        return False
    if val == "":
        if empty:
            return True
        else:
            print(section + ": Invalid " + name + "value : empty string")
            return False
    try:
        parameters[section].getfloat(name)
    except ValueError:
        print(section + ": Invalid " + name + " value " + val)
        return False
    return True


def check_string(parameters, section, name, values=None, empty=True):
    val = parameters.get(section, name, fallback=None)
    if val is None:
        print(section + ": " + name + " not found")
        return False
    if val == "":
        if empty:
            return True
        else:
            print(section + ": Invalid " + name + "value : empty string")
            return False
    if values:
        if val not in values:
            print(section + ": Invalid " + name + " value " + val)
            return False
    return True


def check_time(parameters, section, name, empty=True, chop=6):
    val = parameters.get(section, name, fallback=None)
    if val is None:
        print(section + ": " + name + " not found")
        return False
    if val == "":
        if empty:
            return True
        else:
            print(section + ": Invalid " + name + "value : empty string")
            return False
    dt_format = ""
    if chop > 0: dt_format += "%Y"
    if chop > 1: dt_format += "-%m"
    if chop > 2: dt_format += "-%d"
    if chop > 3: dt_format += " %H"
    if chop > 4: dt_format += ":%M"
    if chop > 5: dt_format += ":%S"
    if chop > 6: dt_format += ".%f"
    try :
        datetime.strptime(val, dt_format)
    except ValueError:
        print(section + ": Invalid " + name + "value : " + val)
        return False
    return True


def get_list(parameters, section, name, check=None):
    if parameters[section][name] == '':
        return list()
    ch = [c.strip() for c in parameters[section][name].split(',')] 

    if check is not None:
        space_warning = [c for c in ch if check in c]
        if len(space_warning) != 0:
            print(section + ": " + name + " contains elements with space:" 
                  + ",".join(space_warning))
    return ch
