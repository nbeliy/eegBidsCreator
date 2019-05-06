from datetime import datetime, date
import struct

from DataStructure.Generic.Channel import GenChannel


class Channel(GenChannel):
    __slots__ = ["_type", "_specification", "_filter"]
    """ Dictionary of standard SI prefixes
        (as defined in EDF+ standard)
    """
    _SIprefixes = {24: 'Y', 21: 'Z', 18: 'E', 15: 'P', 12: 'T', 9: 'G',
                   6: 'M', 3: 'K', 2: 'H', 1: 'D', 0: '', -1: 'd', -2: 'c',
                   -3: 'm', -6: 'u', -9: 'n', -12: 'p', -15: 'f', -18: 'a',
                   -21: 'z', -24: 'y'}
    """ Inverted dictionary of standard SI prefixes
        (as defined in EDF+ standard)
    """
    _SIorders = {'Y': 24, 'Z': 21, 'E': 18, 'P': 15, 'T': 12, 'G': 9, 'M': 6,
                 'K': 3, 'H': 2, 'D': 1, 0: '', 'd': -1, 'c': -2, 'm': -3,
                 'u': -6, 'n': -9, 'p': -12, 'f': -15, 'a': -18, 'z': 21,
                 'y': -24}

    def __init__(self, Base=None, Type="", Specs="", Filter=""):
        if isinstance(Base, GenChannel):
            super(Channel, self).__copy__(Base)
            self._type = Type
            self._specification = Specs
            self._filter = Filter
            if "°" in self._unit:
                self._unit = self._unit[:self._unit.index("°")]\
                        + "deg" + self._unit[self._unit.index("°") + 1:]
        else:
            super(Channel, self).__init__()
            self._type = ""
            self._specification = ""
            self._filter = ""

    def Label(self):
        if (self._type in ["EEG", "ECG", "EOG", "ERG", "EMG", "MEG", "MCG"]):
            return self._type+" "+self._name
        else:
            return self._name

    def GetTransducer(self):
        return self._specification

    def GetFilter(self):
        return self._filter


class EDF(object):
    __slots__ = ["Type", "Patient", "Record", "StartTime", "RecordDuration",
                 "Channels", "Annotations", "Data",
                 "__file", "__path", "__prefix",
                 "__records", "__aDate", "__EDFplus"]

    def __init__(self, path, prefix, AnonymDate=None):
        self.__path = path
        self.__prefix = prefix
        self.__file = None
        self.Patient = {"Code": "X", "Sex": "X", "Birthdate": "X", "Name": "X"}
        self.Record = {"StartDate": datetime.min, "Code": "X",
                       "Technician": "X", "Equipment": "X"}
        self.StartTime = datetime.min
        self.RecordDuration = 1.
        self.Channels = []
        self.Annotations = []
        self.Data = []
        self.__records = 0
        self.__aDate = AnonymDate
        self.__EDFplus = False

    def __del__(self):
        if self.__file is not None:
            self.__file.close()

    def SetEDFplus(self, value=True):
        """
        sets format to EDF+

        Parameters
        ----------
        value : bool, True
            if true, choosen format will be EDF+
        """
        self.__EDFplus = value

    def SetStartTime(self, starttime):
        self.StartTime = starttime.replace(microsecond=0)

    def AddChannel(self, name, resolution=1, unit='',
                   comments='', frequency=1, Type=""):
        self.Channels.append(Channel(name, resolution, unit,
                                     comments, frequency, Type))

    def AddEvent(self, name, date, duration=0, channel=0, description=''):
        ev = {"Name": name, "Date": (date-self.StartTime).total_seconds(),
              "Duration": duration, "Description": description}
        self.Annotations.append(ev)

    def PatientId(self):
        d = ""
        if type(self.Patient["Birthdate"]) == str:
            d = self.Patient["Birthdate"].replace(" ", "_")
        elif type(self.Patient["Birthdate"]) == date:
            self.Patient["Birthdate"].strftime("%d-%b-%Y")
        else:
            d = "X"

        name = self.Patient["Name"]
        if name == self.Patient["Code"] or name == "":
            name = "X"
        return (self.Patient["Code"].replace(" ", "_")
                + " " + self.Patient["Sex"] + " " + d
                + " " + name.replace(" ", "_"))[:80]

    def RecordId(self):
        d = ""
        if self.__aDate is not None\
                or self.Record["StartDate"] == datetime.min:
            d = "X"
        else:
            d = self.Record["StartDate"].strftime("%d-%b-%Y")
        res = "Startdate " + d.upper() + " "
        lenght = 80 - len(res) - 3
        strings = [self.Record["Code"].replace(" ", "_"),
                   self.Record["Technician"].replace(" ", "_"),
                   self.Record["Equipment"].replace(" ", "_")]
        for i in range(0, len(strings)):
            if strings[i] == "":
                strings[i] = "X"
        while (lenght < len(strings[0]) + len(strings[1]) + len(strings[2])):
            i = strings.index(max(strings, key=lambda p: len(p)))
            strings[i] = strings[i][:-1]

        return (res+" ".join(strings))[:80]

    def WriteEvents(self):
        if len(self.Annotations) == 0:
            return
        f = open(self.__path+"/"+self.__prefix+"_events.edf", "wb")
        self.__writeUpperBlock(f, 1)
        f.seek(236, 0)
        f.write("{:<8d}".format(1).encode("ascii"))
        f.seek(256)
        f.write("{:<16s}".format("EDF Annotations").encode("ascii"))
        f.write("{:<80s}".format(" ").encode("ascii"))
        f.write("{:<8s}".format(" ").encode("ascii"))
        f.write("{:<8d}".format(-32768).encode("ascii"))
        f.write("{:<8d}".format(32767).encode("ascii"))
        f.write("{:<8d}".format(-32768).encode("ascii"))
        f.write("{:<8d}".format(32767).encode("ascii"))
        f.write("{:<80s}".format(" ").encode("ascii"))

        pos = f.tell()
        # Number of samples in record, to be calculated later
        f.write("{:<8s}".format(" ").encode("ascii"))
        f.write("{:<32s}".format(" ").encode("ascii"))

        # Start of events
        f.write("{:+f}".format(0).encode("utf_8")
                + b'\x14\x14' + "Recording starts".encode("utf_8")
                + b'\x14\x00')
        for ev in self.Annotations:
            f.write("{:+}".format(ev["Date"]).encode("utf_8"))
            if ev["Duration"] > 0:
                f.write(b'\x15'+"{}".format(ev["Duration"]).encode("utf_8"))
            f.write(b'\x14'+"{}".format(ev["Name"]).encode("utf_8"))
            if (ev["Description"] != ""):
                f.write(b'\x14'+"{}".format(ev["Description"]).encode("utf_8"))
            f.write(b'\x14\x00')

        if f.tell() % 2 != 0:
            f.write(b'\x00')
        size = int(f.tell()/2 - 256)
        f.seek(pos)
        f.write("{:<8d}".format(size).encode("utf_8"))
        f.close()

    def WriteHeader(self):
        self.__file = open(self.__path+"/"+self.__prefix+"_eeg.edf", "wb")
        if self.__EDFplus:
            n_channels = len(self.Channels)+1
        else:
            n_channels = len(self.Channels)
        self.__writeUpperBlock(self.__file, n_channels)
        # [16] Label in format Type Emplacement
        for ch in self.Channels:
            self.__file.write("{:<16s}".format(ch.Label())
                              .encode("ascii")[:16])
        if self.__EDFplus:
            self.__file.write("{:<16s}".format("EDF Annotations")
                              .encode("ascii"))
        # [80] Transducer type
        for ch in self.Channels:
            self.__file.write("{:<80s}".format(ch.GetTransducer())
                              .encode("ascii")[:80])
        if self.__EDFplus:
            self.__file.write("{:<80s}".format(" ").encode("ascii")[:80])
        # [8]    Physical dimensions (i.e. units)
        for ch in self.Channels:
            self.__file.write("{:<8s}".format(ch.GetUnit())
                              .encode("ascii")[:8])
        if self.__EDFplus:
            self.__file.write("{:<8s}".format(" ").encode("ascii"))
        # [8]    Physical minimum
        for ch in self.Channels:
            self.__file.write("{:<8f}".format(ch.GetPhysMin())
                              .encode("ascii")[:8])
        if self.__EDFplus:
            self.__file.write("{:<8d}".format(-32768).encode("ascii"))
        # [8]    Physical maximum
        for ch in self.Channels:
            self.__file.write("{:<8f}".format(ch.GetPhysMax())
                              .encode("ascii")[:8])
        if self.__EDFplus:
            self.__file.write("{:<8d}".format(32767).encode("ascii"))
        # [8]    Digital Minimum
        for ch in self.Channels:
            self.__file.write("{:<8d}".format(ch.GetDigMin())
                              .encode("ascii"))
        if self.__EDFplus:
            self.__file.write("{:<8d}".format(-32768).encode("ascii"))
        # [8]    Digital maximum
        for ch in self.Channels:
            self.__file.write("{:<8d}".format(ch.GetDigMax()).encode("ascii"))
        if self.__EDFplus:
            self.__file.write("{:<8d}".format(32767).encode("ascii"))
        # [80]   Prefiltering
        for ch in self.Channels:
            self.__file.write("{:<80s}".format(ch.GetFilter())
                              .encode("ascii")[:80])
        if self.__EDFplus:
            self.__file.write("{:<80s}".format(" ").encode("ascii"))
        # [8]    Number of samples per record: Recor duration*Frequency
        for ch in self.Channels:
            size = int(ch.GetFrequency()*self.RecordDuration)
            self.__file.write("{:<8d}".format(size).encode("ascii")[:8])
        if self.__EDFplus:
            self.__file.write("{:<8s}".format("8").encode("ascii"))
        # [32]   Reserved
        for ch in self.Channels:
            self.__file.write("{:<32s}".format(" ").encode("ascii")[:32])
        if self.__EDFplus:
            self.__file.write("{:<32s}".format(" ").encode("ascii"))

    def __writeUpperBlock(self, f, n_signal):
        # [0-7,8]        Version of data format, always '0'
        f.write("{:<8d}".format(0).encode("ascii"))
        # [8-87, 80]     Local patient identification
        f.write("{:<80s}".format(self.PatientId()).encode("ascii"))
        # [88-167, 80]   Local recording identification
        f.write("{:<80s}".format(self.RecordId()).encode("ascii"))
        # [168-175,8]    Start date (reference time)
        if self.__aDate is not None:
            d = self.__aDate
        else:
            d = self.StartTime
        if d.year < 1985:
            d = d.replace(year=(d.year + 100))
        f.write("{:<8s}".format(d.strftime("%d.%m.%y")).encode("ascii"))
        # [176-183,8]    Start time (as in metadata)
        f.write("{:<8s}".format(d.strftime("%H.%M.%S")).encode("ascii"))
        # [184-191,8]    Number of bytes in header
        f.write("{:<8d}".format(256+256*n_signal).encode("ascii"))
        # [192-235,44]   EDF+ identifier
        # ('EDF+C' for continous, 'EDF+D' for discontinious)
        if self.__EDFplus:
            f.write("{:<44s}".format("EDF+C").encode("ascii"))
        else:
            f.write("{:<44s}".format(" ").encode("ascii"))
        # [236-243,8]    Number of data records, -1 for unknown
        f.write("{:<8d}".format(-1).encode("ascii"))
        # [244-251,8]    Duration of data record
        f.write("{:<8g}".format(self.RecordDuration).encode("ascii"))
        # [252-255,4]    Number of signals (channels) in record
        f.write("{:<4d}".format(n_signal).encode("ascii"))

    def WriteDataBlock(self, data, start):
        if len(data) != len(self.Channels):
            raise Exception("EDF: mismuch data array dimensions")
        records = int(len(data[0]) / (self.RecordDuration
                      * self.Channels[0].GetFrequency())
                      )
        blocks = list()
        total_block_size = 0
        for i, c in enumerate(self.Channels):
            loc_rec = len(data[i])
            loc_rec /= self.RecordDuration * c.GetFrequency()
            loc_rec = int(loc_rec)
            if records != loc_rec:
                raise Exception(
                        "{}: number of records ({}) different "
                        "from other channels ({})"
                        .format(c.GetName(), loc_rec, records))
            blocks.append(int(self.RecordDuration * c.GetFrequency()))
            total_block_size += blocks[-1]
        if self.__EDFplus:
            total_block_size += 8

        dt = (start - self.StartTime).total_seconds()
        start_pos = self.__file.tell()
        for r in range(0, records):

            s = self.__file.tell()
            for d, block_size, ch in zip(data, blocks, self.Channels):
                self.__file.write(struct.pack("<"+"h"*block_size,
                                  *d[r*block_size:(r+1)*block_size]))
            if self.__EDFplus:
                t_stamp = format(self.RecordDuration*r + dt, '+13f')\
                        .encode("utf_8").strip()[0:13]
                t_stamp += b'\x14\x14\x00' + b'\x00'*(16 - len(t_stamp) - 3)
                self.__file.write(t_stamp)

            self.__records += 1
            written = self.__file.tell() - s
            if written != total_block_size*2:
                raise Exception("Record {} (at {}sec)Written {} bytes, "
                                "expected to write {}"
                                .format(r, dt, written, total_block_size * 2))

        written = self.__file.tell() - start_pos
        if written != records*total_block_size*2:
            raise Exception("EDF: Written {} bytes, expected to write {}"
                            .format(written, records*total_block_size * 2))
        return written

    def Close(self):
        self.__file.seek(236)
        self.__file.write("{:<8d}".format(self.__records).encode("ascii"))
        self.__file.close()
        self.__file = None

    def AddNewSegment(self, date, channel=0, description=''):
        pass
