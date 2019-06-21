############################################################################# 
## MEEG contains all nessesary routines to manipulate SPM12 MEEG format
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


from  scipy.io import savemat
from scipy.io.matlab.mio5_params import MatlabObject
from datetime import datetime
import sys
import numpy
import struct
import logging

from numpy.core.records import fromarrays

Logger = logging.getLogger(__name__)

class MEEG(object):
    __slots__ = ["__headerFile", "__dataFile", "__frequency", "__aDate", "__D", "__channels", "__events", "__startTime", "__duration", "__path", "__file"] 
    #SPM12 accepts following types:
    # EOG: EOG, VEOG, HEOG
    # ECG: ECG,EKG
    # REF: REF, REFMAG, REFGRAD, REFPLANAR
    # MEG: MEG, MEGMAG, MEGGRAD
    # MEGANY: MEGANY, MEGPLANAR
    # MEGCOMB
    # FILTERED: MEEG, REF, EOG, ECG, EMG, LFP, PHYS, ILAM, SRC
    # 
    __chanTypes = ['MEGPLANAR', 'MEGMAG', 'MEGGRAD', 'MEGCOMB', 'MEG',
                'EEG','EOG', 'ECG', 'EMG', 'LFP', 'SRC', 
                'PHYS', 'ILAM', 'OTHER', 'REF', 'REFMAG', 'REFGRAD']
    def __init__(self, path, prefix, AnonymDate=None):
        self.__headerFile   = prefix+"_eeg.mat"
        self.__dataFile     = prefix+"_eeg.dat"
        self.__path         = path
        self.__aDate        = AnonymDate
        self.__frequency    = 1
        self.__events       = list()
        self.__channels     = list()
        self.__D            = dict()
        self.__startTime    = datetime.min
        self.__file = None
        
    def SetStartTime(self, time):
        self.__startTime = time
        if self.__aDate != None:
            time = self.__aDate

    def SetDuration(self, duration):
        self.__duration = duration

    def AddFrequency(self, freq):
        if type(freq) != int:
            raise Exception(__name__+": Only integer frequency is supported")
        self.__frequency = freq

    def GetFrequency(self):
        return self.Header.CommonInfo.GetFrequency()

    def InitHeader(self, Parameters = None):
        Logger.info("Creating eeg.mat header file")
        self.__file = open (self.__path+"/"+self.__dataFile, "bw")
        self.__D = {
            "type":"continuous",
            "data":{},
            "Nsamples" : float(round(self.__duration*self.__frequency)),
            "Fsample":  float(self.__frequency),
            "timeOnset": float(self.__startTime.microsecond*1e-6),
            "fname":self.__headerFile,
            "path": self.__path,
            "trials": [],
            "channels": {},
            "sensors": {},
            "fiducials":{},
            "transform": {"ID":"time"},
            "history": {},
            "other":    {
                'info': {
                    'date':[float(self.__startTime.year), float(self.__startTime.month), float(self.__startTime.day)],
                    'hour':[float(self.__startTime.hour), float(self.__startTime.minute), float(self.__startTime.second)]
                        }
                        },
            "condlist": [],
            "montage":  {}    
            }


    def AppendChannel(self, channel):
        #fields: 'label'        'bad'    'type'        'X'  'y'      'label'    
        spm_type = ''
        or_type = channel.GetType()
        if 'EKG' in or_type:
            or_type = 'ECG'
        for t in self.__chanTypes:
            if t in or_type:
                spm_type = t
                break
        if spm_type == '':
            spm_type = 'OTHER'
        ch = ( channel.GetName(), 0, spm_type, (), (), channel.GetUnit())   
        self.__channels.append(ch)

    def WriteChannels(self):
        self.__D['channels'] = numpy.array(self.__channels, 
                    dtype=[('label',object),('bad',object),('type',object),
                            ('X_plot2D',object),('Y_plot2D',object),('units',object)])

    def AppendEvent(self, event):
        ev = (event.GetName(), 0, event.GetOffset(self.__startTime), event.GetDuration())
        self.__events.append(ev)

    def WriteEvents(self):
        self.__events = numpy.array(self.__events,
            dtype=[('type',object),('value',object),('time',object),('duration',object)])
        self.__D['trials'] = numpy.array([('undefined', 0., 1, 0, self.__events, [])],
            dtype=[('label',object),('onset',object),
                    ('repl',object),('bad',object),
                    ('events',object),('tag',object)])

    def WriteHeader(self):
        f_data = numpy.array(
                [(self.__path+self.__dataFile, 
                [len(self.__channels),int(self.__duration*self.__frequency)],
                16, 0 if sys.byteorder=='little' else 1, 0, [1.,1.], 1, 0, 'rw')],
            dtype=[('fname', object),('dim', object),('dtype',float),
                ('be',float), ('offset',float), ('pos', object),
                ('scl_slope', float), ('scl_inter', float),('permission',object)]
            )
        self.__D['data'] = MatlabObject(f_data, 'file_array')
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
