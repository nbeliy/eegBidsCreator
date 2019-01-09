
#For reading and decoding binary data
import struct
import sys

Types = {0: "any", 1:"rectangle", 2:"point", 3:"string", 4:"bool", 5:"byte", 6:"word", 7:"dword", 
        8:"long", 9:"float", 10:"double", 11:"adouble", 12:"reference", 13: "parcel",
        14:"time", 15:"timespan", 16:"void", 17:"action", 18:"specifier", 19:"aword",
        20:"abyte",
        1000:"resend", 2000:"events", 2001:"evsttime" }


class Parcel(object):
    """Generic ontainer for a set of data"""
    __slots__ = ["__stream",#Stream containing data
                "__size",   #Total size of container in bits
                "__type",   #Type of the container
                "__version",#Version of container
                "__entries",#List of contents of container
                "__start",  #position of the first bit of container
                "__name",   #Name of the parcel, default est '/'
                "__parent"  #Parent parcel
            ] 

    def __str__(self):
        return "Parcel <{0}>, starting at {1}, of size {2}, containing {3} objects".format(
            self.__name, hex(self.__start), hex(self.__size), len(self.__entries))

    def __repr__(self):
        return "{0}: \n{1}".format(self.pwd(), self.__entries)

    def __init__(self, Stream, Name=None, Start=None, Parent=None):
        self.__stream = Stream #How to test if stream is readable
        if Start == None:
            self.__start  = Stream.tell()
        else:
            self.__start  = Start
            Stream.seek(Start)
        if Name == None:
            self.__name = "//"
        else:
            self.__name = Name
        self.__parent = Parent

        # [0:2] Ushort(H) version
        # [2:6] Uinit(I)  size
        # [6:8] Ushort(H) type
        head = Stream.read(8)
        self.__version, self.__size, self.__type = struct.unpack("<HIH",head)
        self.__entries = []

        while Stream.tell() < self.__size+self.__start:
            self.__entries.append(Entry(Stream,Parent=self))
        
        if Stream.tell() != self.__size+self.__start:
            raise Exception("Declared size {0} mismatch number of readed bytes {1}".format(
                        hex(self.__size), hex(Stream.tell() - self.__start)  ))

    def pwd(self):
        """Returns the path to this container"""
        string = self.__name
        p = self.__parent
        while p != None:
            string = p.__name+"/"+string
            p = p.parent()
        return string

    def ls(self, title = ""):
        """Returns a list of wrappers (entries) in this container, matching the given title, if title is '', then fouu list of wrappers is returned"""
        res = []
        for en in self.__entries:
            if title == "" or en.name() == title or en.name() == (title+'\0'):
                res.append(en)
        return res

    def get(self, title, index=0):
        """Return data from a wrapper given its name and index"""
        count = 0
        for en in self.__entries:
            if en.name() == title or en.name() == (title+'\0'):
                if index == count: return en.read()
                count = count+1
        raise Exception("Index {}/{} out of range for container {}".format(title,count, self.__name))

    def getlist(self, title = ""):
        """Return a list of data from wrappers matching the given title"""
        res = []
        for en in self.__entries:
            if title == "" or en.name() == title or en.name() == (title+'\0'):
                res.append(en.read())
        return res
            
    def parent(self):
        """Return the parent of this parcel"""
        return self.__parent

    def ls_r(self, level = 0):
        """Iteratively printout the contents of this Parcel and its sub-parcels"""
        offset = ""
        marker = '\t'
        for i in range(0, level):
            offset = offset+marker
        print (offset+str(self))

        offset = offset+marker
        for c in self.__entries:
            if c.type() == 13:
                c.read().ls_r(level+1)
            else:
                print(offset+str(c)+"<"+str(c.read())+">")


from DataStructure.Embla.Event import ReadEvents
from DataStructure.Embla.Event import ReadEventsStartTime

class Entry(object):
    """A wrapper of a generic data"""
    __slots__ = ["__size", "__dsize", "__type", "__stype", "__readed", "__data", "__start", "__name", "__parent", "__stream"]

    def __str__(self):
        string = "{0}({1})".format(self.__stype, self.__type)
        if not self.__readed:
            string = string+'*'
        return string+"<{0}>".format(self.__name)

    def __repr__(self):
        return "{0}, starting at {1}, of size {2}({3})".format(str(self), hex(self.__start), hex(self.__size), hex(self.__dsize))
    
    def __init__(self, Stream, Parent, Start=None):
        if Start == None:
            self.__start  = Stream.tell()
        else:
            self.__start  = Start
            Stream.seek(Start)
        self.__stream = Stream
        self.__parent = Parent
        self.__readed = False

        # [0:4]     int(i)      size
        # [4:8]     int(i)      data size
        # [8:10]    Ushort(H)   type
        # [10:12]   short(h)    unused
        head = Stream.read(10)
        Stream.seek(2,1)
        self.__size, self.__dsize, self.__type = struct.unpack("<iiH", head)
        if not self.__type in Types:
            self.__type = 0
        self.__stype = Types[self.__type]
            
        self.__data  = None
        Stream.seek(self.__dsize,1)
        self.__name = Stream.read(self.__size - self.__dsize - 12).decode("ascii").strip('\0')

    def read(self):
        """Read and returns data, formatted folowing the type"""
        if not self.__readed:
            Stream = self.__stream
            Stream.seek(self.__start+12, 0)
            if self.__type == 4:
                data = (Stream.read(self.__dsize) != 0) 
            elif self.__type == 3:
                data = Stream.read(self.__dsize).decode('1252').strip('\0')
            elif self.__type == 6:
                data = struct.unpack("<H",Stream.read(self.__dsize))[0]
            elif self.__type == 7:
                data = struct.unpack("<I",Stream.read(self.__dsize))[0]
            elif self.__type == 8:
                data = struct.unpack("<l",Stream.read(self.__dsize))[0]
            elif self.__type == 13:
                data = Parcel(Stream, Name= self.__name, Start=Stream.tell(), Parent=self.__parent)
            elif self.__type == 15:
                #Readed data contains 16 bits, if 8 are seconds, 4 are miliseconds,
                #the remaining 2 are always composed of \xbbT\x06t
                #If timespan contains only seconds, lenth is 8(long long) 
                d = Stream.read(self.__dsize)
                if (len(d) == 16):
                    sec, mils = struct.unpack("<qi",d[0:12])
                    data = float(sec) + float(mils)/1000
                elif (len(d) == 8):
                    sec = struct.unpack("<q",d[0:8])
                    data = float(sec) 
                else:
                    raise Exception("Unable to parce timespan from string {}".format(d))
            elif self.__type == 2000:
                data = ReadEvents(Stream.read(self.__dsize))
            elif self.__type == 2001:
                data = ReadEventsStartTime(Stream.read(self.__dsize))
            else:
                data = Stream.read(self.__dsize)
        else :
            self._readed = True       
        return data

    def type(self): return self.__type
    def name(self): return self.__name


