import struct
from datetime import datetime

from DataStructure.Channel import Channel
from DataStructure.Channel import Marks

#f = open("testdata.ebm", "rb")
#f = open("../data_test/EEG/BL/c6902c41-642b-4dd2-88b2-81e03feba944/C3.ebm", "rb")

ch = Channel("data_example/embla_data/C3.ebm")

print(str(ch))
print("RawRange:", ch.RawRange[0:10])
print("TransRange:", ch.TransRange[0:10])
print("SigType:", ch.SigType[0:10])
print("SigRef:", ch.SigRef[0:10])
print("LowHight:", ch.LowHight[0:10])

print(ch.getTime(0,0), ch.getValue(0,0))
print(ch.getTime(1,0), ch.getValue(1,0))
print(ch.getTime(2,0), ch.getValue(2,0))
print(ch.getTime(3,0), ch.getValue(3,0))
print(ch.getTime(4,0), ch.getValue(4,0))
print("####################")
print(ch.getTime(0,1), ch.getValue(0,1))
print(ch.getTime(1,1), ch.getValue(1,1))
print(ch.getTime(2,1), ch.getValue(2,1))
print(ch.getTime(3,1), ch.getValue(3,1))
print(ch.getTime(4,1), ch.getValue(4,1))
print("####################")
print(ch.getRelPoint(1234))
print(ch.getTime(1234), ch.getValue(1234))
print("####################")
print(ch.getRelPoint(99))
print(ch.getTime(99), ch.getValue(99))

