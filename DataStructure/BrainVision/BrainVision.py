############################################################################# 
## BrainVision contains a BrainVision class definitions, which allows
## the manipulation of corresponding EEG data format.
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


from DataStructure.BrainVision.Recording import Header 
from DataStructure.BrainVision.Events import MarkerFile
from DataStructure.BrainVision.Data import DataFile

class BrainVision(object):
    __slots__ = ["Header", "MarkerFile", "DataFile"]
    
    def __init__(self, path, prefix, AnonymDate=None):
        self.Header     = Header(path, prefix)
        self.MarkerFile = MarkerFile(path, prefix)
        self.MarkerFile.SetAnonymDate(AnonymDate)
        self.DataFile   = DataFile(path, prefix)

    def SetEncoding(self, encoding):
        encs = ["UTF-8", "ANSI"]
        if encoding not in encs:
            raise Exception("BrainVision: encodind {} is not supported".format(encoding))
        self.Header.CommonInfo.CodePage = encoding
    
    def GetEncoding(self):
        return self.Header.CommonInfo.CodePage

    def SetDataFormat(self, encoding):
        encs = ["IEEE_FLOAT_32", "INT_16", "UINT_16"]
        if encoding not in encs:
            raise Exception("BrainVision: data format {} is not supported".format(encoding))
        self.Header.BinaryInfo.BinaryFormat = encoding
    
    def GetDataFormat(self):
        return self.Header.BinaryInfo.BinaryFormat

    def AddFrequency(self, freq):
        if type(freq) != int:
            raise Exception(__name__+": Only integer frequency is supported")
        self.Header.CommonInfo.AddFrequency(freq)
    def GetFrequency(self):
        return self.Header.CommonInfo.GetFrequency()

    def SetEndian(self, useLittle):
        if useLittle:
            self.Header.BinaryInfo.UseBigEndianOrder = "NO"
        else:
            self.Header.BinaryInfo.UseBigEndianOrder = "YES"

    def AddEvent(self, name, date, duration = 0, channel = 0, description = ''):
        self.MarkerFile.AddMarker(name, date, duration, channel, description)
    
    def AddNewSegment(self, date, channel  = 0, description = ''):
        self.MarkerFile.AddNewSegment(self, date, channel, description)
