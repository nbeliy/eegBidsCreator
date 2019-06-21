############################################################################# 
## check_configuration is a script that verifies if configuration file
## passed as argument is a valid file for eegBidsCreator
############################################################################# 
## Copyright (c) 2018-2019, University of Liège
## Author: Nikita Beliy
## Owner: Liege University https://www.uliege.be
## Credits: [{credit_list}]
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


import os
import tools.cfi as cfi


def check_configuration(filename):
    """
    Check the validity of configuration file

    Parameters
    ----------
    filename: str
        path to a configuration file
    
    Returns
    -------
    int:
        0 if file is valid, 1 overwise
    """

    parameters = cfi.default_parameters()
    cfi.read_parameters(parameters, filename)
    if cfi.check_configuration(parameters):
        print("File " + filename + " seems to be correct")
        return 0
    else:
        print("File " + filename + " contains errors")
        return 1


if __name__ == "__main__":
    os.sys.exit(check_configuration(os.sys.argv[1]))
