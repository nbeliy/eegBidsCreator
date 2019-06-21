############################################################################# 
## exceptions defines standard exception classes expected to occure during
## eegBidsCreator execution
############################################################################# 
## Copyright (c) 2018-2019, University of Liège
## Author: Nikita Beliy
## Owner: Liege University https://www.uliege.be
## Version: 0.76
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

class BIDSexception(Exception):
    """
    Base class for other exceptions
    code will serve as return code of programm    
    """
    code = 1

class CfgFileError(BIDSexception):
    """
    Raises if there errors in ini file
    """
    code = 2

class IOError(BIDSexception):
    """
    Raises if unable to acess/copy/move files
    """
    code = 3

class RecordingExistsError(BIDSexception):
    """
    Raises if recording exists in the output
    """
    code = 10


class EegFormatError(BIDSexception):
    """
    Raises if there error with input file format
    """
    code = 20

class UnknownFormatError(EegFormatError):
    """
    Raises if input file format is unknown
    """
    code = 21

class NotImplementedFormatError(EegFormatError):
    """
    Raises if format to convert is not implemented
    """
    code =22

class TimeError(BIDSexception):
    """
    Raises if there an error related to time
    """
    code = 30

class RunError(BIDSexception):
    """
    Raises if there an error related to runs definition
    """
    code = 40

class UnableToSplitRunsError(RunError):
    """
    Raises if unable to split recording into runs
    """
    code = 41

class NoValidRunsError(RunError):
    """
    Raises if no valid runs are found
    """
    code = 42

class PluginError(BIDSexception):
    """
    Generic plugin error
    """
    code = 100

class PluginNotfound(PluginError):
    """
    Raises if plugin file not found
    """
    code =101

class PluginModuleNotFound(PluginError):
    """
    Raises if no plugin modules found in plugin file
    """
    code = 102

class RecordingEPError(PluginError):
    """
    Raises if error occured in RecordingEP plugin
    """
    code = 110

class ChannelsEPError(PluginError):
    """
    Raises if error occured in ChannelsEP plugin
    """
    code = 120

class EventsEPError(PluginError):
    """
    Raises if error occured in EventsEP plugin
    """
    code = 130

class RunsEPError(PluginError):
    """
    Raises if error occured in RunsEP plugin
    """
    code = 140

class DataEPError(PluginError):
    """
    Raises if error occured in DataEP plugin
    """
    code = 150
