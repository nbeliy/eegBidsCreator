from  scipy.io import savemat
from scipy.io.matlab.mio5_params import MatlabObject
from datetime import datetime
import numpy
import struct

from numpy.core.records import fromarrays

class MEEG(object):
    __slots__ = ["__headerFile", "__dataFile", "__frequency", "__aDate", "__D", "__events", "__startTime", "__duration", "__path", "__file"] 


    def __init__(self, path, prefix, AnonymDate=None):
        self.__headerFile   = prefix+"_eeg.mat"
        self.__dataFile     = prefix+"_eeg.dat"
        self.__path         = path
        self.__aDate        = AnonymDate
        self.__frequency    = 1
        self.__events       = list()
        self.__D            = {
            "type":"continuous",
            "data":[],
            "Nsamples":0,
            "Fsample":0,
            "timeOnset": 0.0,
            "fname":prefix+"_eeg.mat",
            "path": path,
            "trials": [],
            "channels": [],
            "sensors": {},
            "fiducials":{},
            "transform": {"ID":"time"},
            "history": {},
            "other": [],
            "condlist": [],
            "montage":  {}    
        }
        self.__startTime = datetime.min
        self.__file = open (self.__path+"/"+self.__dataFile, "bw")
        
    def SetStartTime(self, time):
        self.__startTime = time
        if self.__aDate != None:
            time = self.__aDate
        self.__D['other'] = {'info':{'date':[time.year, time.month, time.day],
                 'hour':[time.hour, time.minute, time.second]}}

    def SetDuration(self, duration):
        self.__duration = duration

    def AddFrequency(self, freq):
        if type(freq) != int:
            raise Exception(__name__+": Only integer frequency is supported")
        self.__frequency = freq

    def GetFrequency(self):
        return self.Header.CommonInfo.GetFrequency()

    def AppendChannel(self, channel):
        #fields: 'label'        'bad'    'type'        'X'  'y'      'label'    
        ch = ( channel.GetName(), 0, channel.GetType(), 0, 0, channel.GetUnit())   
        self.__D["channels"].append(ch)

    def AppendEvent(self, event):
        ev = (event.GetName(), 0, event.GetOffset(self.__startTime), event.GetDuration())
        self.__events.append(ev)

    def WriteHeader(self):
        f_data = numpy.array(
                [(self.__path+self.__dataFile, 
                [len(self.__D['channels']),int(self.__duration*self.__frequency)],
                16, 0, 0, [1.,1.], 1, 0, 'rw')],
            dtype=[('fname', object),('dim', object),('dtype',float),
                ('be',float), ('offset',float), ('pos', object),
                ('scl_slope', float), ('scl_inter', float),('permission',object)]
            )
        #self.__D['data'] = f_data
        self.__D['data'] = MatlabObject(f_data, 'file_array')
        self.__D['channels'] = numpy.array(self.__D['channels'], 
                    dtype=[('label',object),('bad',object),('type',object),
                            ('X_plot2D',object),('Y_plot2D',object),('units',object)])
        self.__D['Nsamples'] = int(self.__duration*self.__frequency)
        self.__D['Fsample']  = self.__frequency
        self.__D['timeOnset']= self.__startTime.microsecond*1e-6
        
        

    def WriteEvents(self):
        self.__events = numpy.array(self.__events,
            dtype=[('type',object),('value',object),('time',object),('duration',object)])
        self.__D['trials'] = numpy.array([('undefined', 0., 1, 0, self.__events, [])],
            dtype=[('label',object),('onset',object),
                    ('repl',object),('bad',object),
                    ('events',object),('tag',object)])
        savemat(self.__path+self.__headerFile, {'D':self.__D})

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
            self.__file.write(struct.pack('f'*len(data),*d))
