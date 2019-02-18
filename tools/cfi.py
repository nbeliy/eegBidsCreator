import configparser
import logging

Logger = logging.getLogger(__name__)

'''
    Contain initialisation and default configuration file parameters
'''

def default_parameters():
    '''Creates and returns configparser.ConfigParser object 
    containing default configuration'''
    parameters = configparser.ConfigParser()
    #Making keys case-sensitive
    parameters.optionxform = lambda option: option
    #Setting up default values
    parameters['GENERAL'] = {
                            "SessionId"     :"", 
                            "TaskId"        :"", 
                            "AcquisitionId" :"",
                            "JsonFile"      :"", 
                            "OutputFolder"  :".", 
                            "Conversion"    :"",
                            "CopySource"    :"yes",
                            "MemoryUsage"   :"2"
                            }
    parameters['LOGGING'] = {
                            "LogLevel"  :"INFO", 
                            "LogFile"   :"",
                            "Quiet"     :"no"
                            }
    parameters['CHANNELS']= {
                            'WhiteList'   :"",
                            'BlackList'   :"",
                            'MainChannel' :""
                            }
    parameters['EVENTS']  = {
                            'WhiteList'   :"",
                            'BlackList'   :"",
                            "IgnoreOutOfTimeEvents" :"yes",
                            "IncludeSegmentStart"   :"no",
                            "MergeCommonEvents"     :"yes"
                            }
    parameters['DATATREATMENT'] =   {
                            "StartTime"     :"", "EndTime"  :"", 
                            "StartEvent"    :"", "EndEvent" :"",
                                    }
    parameters['RUNS'] =    {
                            "SplitRuns"     :"",
                            "OpeningEvents" :"",
                            "ClosingEvents" :"",
                            "MinSpan"       :"0"
                            }
    parameters['ANONYMIZATION'] =   {
                                    "Anonymize" :"yes",
                                    "StartDate" :"1973-3-01",
                                    "SubjName"  :"John Doe",
                                    "BirthDate" :""
                                    }
    parameters['PLUGINS']       =   {
                                    "Plugin" : ""
                                    }
    parameters['BRAINVISION']   =   {
                                    "Encoding"  :"UTF-8", 
                                    "DataFormat":"IEEE_FLOAT_32", 
                                    "Endian"    :"Little"
                                    }
    parameters['EDF'] = {
                        "DataRecordDuration"    :"10"
                        }
    parameters['MEEG']= {}
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
            raise FileNotFoundError("Unable to open file "+config_file)
    return readed


def check_configuration(parameters):
    '''Check if parameters are valid'''
    if not isinstance(parameters, configparser.ConfigParser):
        raise TypeError("Parameters must be a ConfigParcer instance")
    passed = True
    if parameters["GENERAL"]["Conversion"] not in ["","BrainVision","EDF","MEEG"]:
        print("GENERAL: Invalid conversion format: "+parameters["GENERAL"]["Conversion"])
        passed = False
    if parameters["CHANNELS"]["WhiteList"] != "" and parameters["CHANNELS"]["BlackList"] != "":
        print("CHANNELS: Both White and Black lists are defined")
        passed = False
    if parameters["EVENTS"]["WhiteList"] != "" and parameters["EVENTS"]["BlackList"] != "":
        print("EVENTS: Both White and Black lists are defined")
        passed = False
    if parameters["EVENTS"].getboolean("IncludeSegmentStart") and parameters["CHANNELS"]["MainChannel"] == "":
        print("EVENTS: IncludeSegmentStart is defined but MainChannel is not")
        passed = False

    if parameters["RUNS"]["SplitRuns"] != "":
        if parameters["EVENTS"].getboolean("IgnoreOutOfTimeEvents"):
            print("EVENTS: IgnoreOutOfTimeEvents is incompatible with SplitRuns")
            passed = False
        if parameters["RUNS"]["SplitRuns"] == "Channel":
            if parameters["CHANNELS"]["MainChannel"] == "":
                print("RUNS: Splitting by channel, but MainChannel is not defined")
                passed = False
        elif parameters["RUNS"]["SplitRuns"] == "EventSpan":
            if parameters["RUNS"]["OpeningEvents"] == "":
                print("RUNS: Splitting by event but Event is not defined")
                passed = False
        elif parameters["RUNS"]["SplitRuns"] == "EventLimit":
            opEvl = parameters["RUNS"]["OpeningEvents"].split(',')
            clEvl = parameters["RUNS"]["ClosingEvents"].split(',')
            if len(opEvl) == 0 or len(opEvl) != len(clEvl):
                print("RUNS: Splitting by event start and end but Event and/or EndEvent mismuch dimensions") 
                passed = False
        else :
            print("RUNS: Invalid run splitting mode: "+parameters["RUNS"]["SplitRuns"])
            passed = False

    return passed


