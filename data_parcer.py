import struct
from datetime import datetime

from DataStructure.Channel import Channel
from DataStructure.Channel import Marks

from glob import glob

ch = [Channel(c) for c in glob("data_example/embla_data/*.ebm")]

for c in ch:
    try:
        print(str(c))
        print(c.getTime(202,0), c.getValue(202,0))
        print(c.getTime(202,1), c.getValue(202,1))
        print(c.getRelPoint(1002))
        print(c.getTime(1002), c.getValue(1002))
    except: pass
    print("##############################")

