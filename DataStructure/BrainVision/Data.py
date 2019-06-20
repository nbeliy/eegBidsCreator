############################################################################# 
## Data contains all nesesary routines to write BrainVision data file
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

import struct

class DataFile(object):
    __slots__ = ["__marker", "__endian", "__file", "__prefix", "__path"]

    def __init__(self, path, prefix):
        self.__marker = 'f'
        self.__endian = '<'
        self.__file   = None
        self.__prefix = prefix
        self.__path   = path

    def SetDataFormat(self, dformat):
        if dformat == "INT_16":
            self.__marker = 'h'
        elif dformat == "UINT_16":
            self.__marker = 'H'
        elif dformat == "IEEE_FLOAT_32":
            self.__marker = 'f'
        else:
            raise Exception("BrainVision: Data format {} is not supported".format(dformat))

    def SetEndian(self, endian):
        if endian == "NO":
            self.__endian = '<'
        elif endian == "YES":
            self.__endian = '>'
        else:
            raise Exception("BrainVision: Undefined value {}".format(endian))

    def OpenFile(self):
        self.__file = open (self.__path+"/"+self.__prefix+"_eeg.eeg", "bw")
        
    def WriteBlock(self, data):
        if type(data) != list or type(data[0]) != list:
            raise Exception("BrainVision: Must have nested list [channels][points]")
        for c in data:
            if len(c) != len(data[0]):
                raise Exception("BrainVision: All points list must have same lenght")

        for j in range(0, len(data[0])):
            d = [0]*len(data)
            for k in range(0, len(data)):
                d[k] = data[k][j]
            self.__file.write(struct.pack(self.__endian+self.__marker*len(data),*d))


