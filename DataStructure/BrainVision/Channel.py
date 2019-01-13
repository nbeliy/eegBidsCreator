from DataStructure.Generic.Channel import GenChannel

class BvChannel(GenChannel):
    """ Class containing all information retrieved from ebm file. The data instead to be loaded in the memory, are readed directly from file """
    __slots__ = ["_reference", "_comments"]

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

