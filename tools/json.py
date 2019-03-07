import os
import json
import logging

Logger = logging.getLogger(__name__)

"""Module with functions treating all JSON related staff"""

def loadJson(filename, app=""):
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
    Logger.info("Creating events.json file")
    ev_struct = {
                "responce_time" : {
                    "Description": "Response time measured in seconds. \
A negative response time can be used to represent preemptive responses \
and “n/a” denotes a missed response.",
                    "Units": "second"},
                "value"         : {
                    "Description": "The event TTL trigger value \
(EEG Marker value) associated with an event "},
                "channels"      : {
                    "Description": "Comma separated list of channels triggering an event"
                    }
                }
    return dumpJson(filename, ev_struct)


def participantsJson(filename):
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


