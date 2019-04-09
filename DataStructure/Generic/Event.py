from datetime import datetime
from tools.json import fieldLibrary


def ReplaceInField(In_string, Void="", ToReplace=None):
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


class GenEvent(object):
    """An intendent virtual class serving as parent to other,
    format specific event classes"""
    __base_slots__ = [
            "_name", "_time", "_duration", 
            "_channels", "_baseEvent",
            "libValues"
            ]
    __slots__ = __base_slots__

    FieldsLibrary = fieldLibrary()
    FieldsLibrary.AddField(
          "onset", 
          description="Onset (in seconds) of the event measured "
          "from the beginning of the acquisition of "
          "the first volume in the corresponding task imaging "
          "data file. If any acquired scans have been discarded "
          "before forming the imaging data file, ensure that "
          "a time of 0 corresponds to the first image stored.",
          units="s")
    FieldsLibrary.AddField(
          "duration",
          description="Duration of the event (measured from onset) "
          "in seconds. Must always be either zero "
          "or positive. A \"duration\" value of zero "
          "implies that the delta function or event "
          "is so short as to be effectively modeled "
          "as an impulse.",
          units="s")
    FieldsLibrary.AddField(
          "sample",
          description="Onset of the event according to "
          "the sampling scheme of the recorded modality "
          "(i.e., referring to the raw data file that "
          "the events.tsv file accompanies).",
          activated=False)
    FieldsLibrary.AddField(
          "trial_type",
          description="Primary categorisation of each trial "
          "to identify them as instances of the experimental "
          "conditions. For example: for a response inhibition "
          "task, it could take on values \"go\" and \"no-go\" "
          "to refer to response initiation and response inhibition "
          "experimental conditions.")
    FieldsLibrary.AddField(
          "response_time",
          description="Response time measured in seconds. A negative "
          "response time can be used to represent preemptive "
          "responses and \"n/a\" denotes a missed response.",
          units="s",
          activated=False)
    FieldsLibrary.AddField(
          "stim_file",
          description="Represents the location of the stimulus file "
          "(image, video, sound etc.) presented at the given onset "
          "time. There are no restrictions on the file formats of "
          "the stimuli files, but they should be stored in the "
          "/stimuli folder (under the root folder of the dataset; "
          "with optional subfolders). The values under the stim_file "
          "column correspond to a path relative to \"/stimuli\". "
          "For example \"images/cat03.jpg\" will be translated to "
          "\"/stimuli/images/cat03.jpg\".",
          activated=False)
    FieldsLibrary.AddField(
          "value",
          description="Marker value associated with the event (e.g., "
          "the value of a TTL trigger that was recorded at the onset "
          "of the event).")
    FieldsLibrary.AddField(
          "HED",
          description="Hierarchical Event Descriptor (HED) Tag. "
          "See Appendix III for details.",
          url="https://bids-specification.readthedocs.io/en/latest"
          "/99-appendices/03-hed.html",
          activated=False)
    FieldsLibrary.AddField(
          "channels",
          description="List of channels names that are associated with "
                      "this event")

    def __copy__(self, source):
        if not isinstance(source, GenEvent):
            raise TypeError("Source object must be a daughter of " 
                            + self.__class__.__name__)
        for f in self.__base_slots__:
            setattr(self, f, getattr(source, f))
        self._baseEvent = source

    def __init__(self, Name="", Time=datetime.min, Duration=0):
        self._name = Name
        self._time = Time
        self._duration = Duration
        self._channels = []
        self._baseEvent = self
        self.libValues = self.FieldsLibrary.GetTemplate()

    def SetName(self, Name):
        if not isinstance(Name, str):
            raise TypeError("Name must be a string")
        self._name = Name

    def SetTime(self, Time=None, Duration=None):
        if Time is None:
            Time = self._time
        if Duration is None:
            Duration = self._duration
        if not (isinstance(Duration, int) or isinstance(Duration, float)):
            raise TypeError("Duration must be a number")
        if not isinstance(Time, datetime):
            raise TypeError("Time must be a datetime object")
        self._time = Time
        self._duration = Duration

    def GetName(self, Void="", ToReplace=None):
        return ReplaceInField(self._name, Void, ToReplace)

    def GetTime(self):
        return self._time

    def GetDuration(self):
        return self._duration

    def GetOffset(self, Time):
        if not isinstance(Time, datetime):
            raise TypeError("Time must be a datetime object")
        return (self._time - Time).total_seconds()

    def AddChannel(self, Id):
        if isinstance(Id, list):
            for ref in Id:
                self.AddChannel(ref)
        elif Id not in self._channels:
            self._channels.append(Id)

    def GetChannels(self):
        return self._channels

    def GetChannelsSize(self):
        return len(self._channels)

    def RemoveChannel(self, Id=None):
        if Id is None:
            self._channels = []
        if isinstance(Id, list):
            for ref in Id:
                self.RemoveChannel(ref)
        elif Id in self._channels:
            self._channels.remove(ref)

    def __eq__(self, other):
        if type(other) != type(self):
            raise TypeError("Comparaison arguments must be of the same class")
        if self._time == other._time\
           and self._name == other._name\
           and self._duration == other._duration : 
            return True
        else:
            return False

    def __lt__(self, other):
        if type(other) != type(self):
            raise TypeError("Comparaison arguments must be of the same class")
        if self._time != other._time:
            return self._time < other._time
        if self._name != other._name:
            return self._name < other._name
        if self._duration != other._duration:
            return self._duration < other._duration
        return False

    def __gt__(self, other):
        if type(other) != type(self):
            raise TypeError("Comparaison arguments must be of the same class")
        if self._time != other._time:
            return self._time > other._time
        if self._name != other._name:
            return self._name > other._name
        if self._duration != other._duration:
            return self._duration > other._duration
        return False

    def __ge__(self, other):
        return (self > other or self == other)

    def __le__(self, other):
        return (self < other or self == other)
