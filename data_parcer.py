import struct, math
from datetime import datetime, timedelta
import sys

from DataStructure.Channel import Channel
from DataStructure.Channel import Marks

from glob import glob

#ch = [Channel(c) for c in glob("data_example/embla_data/*.ebm")]
#ch = [Channel(c) for c in glob("../data_test/EEG/BL/c6902c41-642b-4dd2-88b2-81e03feba944/*.ebm")]
ch = [Channel(c) for c in glob("../data_test/EEG/ECG/fd068a73-0527-428f-aeed-9e04fb55ed4b/*.ebm")]

for c in ch:
    try:
        print(str(c))
        print(c.getTime(202,0), c.getValue(202,0))
        print(c.getTime(202,1), c.getValue(202,1))
        print(c.getRelPoint(1002))
        print(c.getTime(1002), c.getValue(1002))
    except: pass
    print("##############################")

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
