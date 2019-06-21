############################################################################# 
## Channel contains the definition of Channel class for BrainVision format
############################################################################# 
## Copyright (c) 2018-2019, University of Liège
## Author: Nikita Beliy
## Owner: Liege University https://www.uliege.be
## Version: 0.74
## Maintainer: Nikita Beliy
## Email: Nikita.Beliy@uliege.be
## Status: developpement
############################################################################# 
## This file is part of eegBidsCreator                                     
## eegBidsCreator is free software: you can redistribute it and/or modify     
## it under the terms of the GNU General Public License as published by     
## the Free Software Foundation, either version 2 of the License, or     
## (at your option) any later version.      
## eegBidsCreator is distributed in the hope that it will be useful,     
## but WITHOUT ANY WARRANTY; without even the implied warranty of     
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the     
## GNU General Public License for more details.      
## You should have received a copy of the GNU General Public License     
## along with eegBidsCreator.  If not, see <https://www.gnu.org/licenses/>.
############################################################################


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

