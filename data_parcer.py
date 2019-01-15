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
    exit(main(os.sys.argv))
