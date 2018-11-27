import struct
from datetime import datetime

from Channel import Channel
from Channel import Marks

#f = open("testdata.ebm", "rb")
f = open("../data_test/EEG/BL/c6902c41-642b-4dd2-88b2-81e03feba944/C3.ebm", "rb")

#Reading header
buff = b''
ch = f.read(1)


while ch != b'\x1a':
    buff = buff+ch
    ch = f.read(1)

if (buff.decode('ascii') == 'Embla data file'):
    print("We reading Embla data file")
elif (buff.decode('ascii') == 'Embla results file'):
    print("We are reading Embla results file")
else:
    print("We are not reading either Embla results or Embla data")
    exit()

ch = f.read(1)

if ch == b'\xff':
    BigEndian = True
    byteorder = 'big'
    byteprefix= '>'
    print("We using big-endian")
elif ch == b'\x00':
    BigEndian = False
    byteorder = 'little'
    byteprefix= '<'
    print("We using little-endian")
else:
    print("Can't determine endian, format problrm?")
    exit()

wideId = False
ch = f.read(1)
if (ch == b'\xff'):
    ch = f.read(4)
    if ch == b'\xff\xff\xff\xff':   
        wideId = True
        print("We using wide Id")
        f.seek(32 - 6,1)
else:
    print("We using normal Id")
    
if wideId :
    base_size = 4
else:
    base_size = 1
ch = Channel(byteprefix, wideId)

while True:
    #print("---------------------")
    start = f.tell()
    if wideId :
        index = f.read(4)
    else:
        index = f.read(2)
        index = index+b'\x00\x00'
        
    if(index == b''):break
    #print(hex(start), index)
    size = f.read(4)
    #print(size)
    size = struct.unpack("<L", size)[0]
    #print("Size:",size)
    data = f.read(size)
    ch.read(index, data)

print(str(ch))
