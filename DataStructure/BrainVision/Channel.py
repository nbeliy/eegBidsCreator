from DataStructure.Generic.Channel import GenChannel

class BvChannel(GenChannel):
    """ Class containing all information retrieved from ebm file. The data instead to be loaded in the memory, are readed directly from file """
    __slots__ = ["_reference", "_comments"]

    "Dictionary of standard SI prefixes (as defined in EDF+ standard)"
    _SIprefixes = {24:'Y', 21:'Z', 18:'E', 15:'P', 12:'T', 9:'G', 6:'M', 3:'K', 2:'H', 1:'D', 0:'', -1:'d', -2:'c', -3:'m', -6:'μ', -9:'n', -12:'p', -15:'f', -18:'a', -21:'z', -24:'y'}
    "Inverted dictionary of standard SI prefixes (as defined in EDF+ standard)"
    _SIorders   = {'Y':24, 'Z':21, 'E':18, 'P':15, 'T':12,'G': 9,'M': 6,'K': 3,'H': 2,'D': 1, 0:'', 'd':-1, 'c':-2, 'm':-3, 'μ':-6, 'n':-9, 'p':-12, 'f':-15, 'a':-18, 'z':21, 'y':-24}

    def __init__(self, Base = None, Reference = "", Comments = ""):
        if isinstance(Base, GenChannel):
            super(BvChannel, self).__copy__(Base)
            self._comments = Comments
            self._reference = Reference
        else:
            super(BvChannel, self).__init__()
            self._reference  = Reference
            self._comments   = Comments

    def GetReference(self):
        return self._reference

    def GetComments(self):
        return self._comments

