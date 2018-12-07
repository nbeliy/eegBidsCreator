import struct
from datetime import datetime

from DataStructure.Channel import Channel
from DataStructure.Channel import Marks

from glob import glob

#ch = [Channel(c) for c in glob("data_example/embla_data/*.ebm")]
ch = [Channel(c) for c in glob("../data_test/EEG/BL/c6902c41-642b-4dd2-88b2-81e03feba944/*.ebm")]

for c in ch:
    try:
        print(str(c))
        print(c.getTime(202,0), c.getValue(202,0))
        print(c.getTime(202,1), c.getValue(202,1))
        print(c.getRelPoint(1002))
        print(c.getTime(1002), c.getValue(1002))
    except: pass
    print("##############################")

