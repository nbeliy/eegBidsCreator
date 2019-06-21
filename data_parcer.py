############################################################################# 
## data_parcer is a script which reads Embla channel file and prints out
## retrieved information
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


import struct, math
from datetime import datetime, timedelta
import os,sys
from DataStructure.Embla.Channel import EbmChannel
from glob import glob
import argparse



def main(argv):
    parser = argparse.ArgumentParser(description='Reads embla channel files (.emb) from given folder and printout the retrieved information')
    parser.add_argument('infiles', default="../data_test/EEG/ECG/fd068a73-0527-428f-aeed-9e04fb55ed4b",
        metavar='file1',
        help='input folder')
    args = parser.parse_args(argv[1:])
    ch = GetChannels(args.infiles)
    for c in ch:
        print("####################")
        print(c)
        print()
    return 0

def GetChannels(path):
    ch = [EbmChannel(c) for c in glob(path+"/*.ebm")]
    ch.sort()
    return ch

def GetExtrema(channel, sequence, raw = False):
    v_min = sys.maxsize
    v_max = -v_min
    for j in range(0, channel.getSize(sequence)):
        v = channel.getValue(j, sequence, raw = raw)
        if v < v_min:
            v_min = v
        if v > v_max:
            v_max = v 
        
    return (v_min, v_max)


if __name__ == "__main__":
    os.sys.exit(main(os.sys.argv))
