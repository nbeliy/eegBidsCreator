############################################################################# 
## cli contain all nessesary routines to parce the command line options
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


import argparse


def parce_CLI(argv, VERSION):
    '''Parce passed array of string and returns resulting 
    argparse.ArgumentParser object.'''
    parser = argparse.ArgumentParser(
            description='Converts EEG files to BIDS standard')
    parser.add_argument('infile',
                        metavar='eegfile', nargs=1,
                        help='input eeg file')
    parser.add_argument('--version',
                        action='version', version='%(prog)s ' + VERSION)

    parser.add_argument('-p, --patient', 
                        metavar='subId', dest='sub', 
                        help='Id of the patient')
    parser.add_argument('-s, --session', 
                        metavar='sesId', dest='ses', 
                        help='Id of the session')
    parser.add_argument('-t, --task', 
                        metavar='taskId', dest='task', 
                        help='Id of the task')
    parser.add_argument('-a, --acquisition', 
                        metavar='acqId', dest='acq', 
                        help='Id of the acquisition')
    parser.add_argument('-r, --run', 
                        metavar='runId', dest='run', 
                        help='Id of the run')

    parser.add_argument('-c, --config', 
                        nargs=1, dest='config_file', 
                        help="Path to configuration file")

    parser.add_argument('-j, --json', 
                        metavar='eegJson', dest='eegJson', 
                        help="A json file with task description")
    parser.add_argument('-o, --output', 
                        nargs=1, dest='outdir', 
                        help='destination folder')

    parser.add_argument('--logfile', 
                        nargs=1, metavar='log.out', 
                        dest='logfile', 
                        help='log file destination')
    parser.add_argument('-q,--quiet', 
                        dest='quiet', action="store_true", 
                        help="Supress standard output")
    parser.add_argument('--log', 
                        dest='loglevel', 
                        choices=["DEBUG", "INFO", "WARNING", 
                                 "ERROR", "CRITICAL"], 
                        help='logging level')

    parser.add_argument('--mem', 
                        nargs=1, type=int, 
                        help='allowed memory usage (in GiB)')

    parser.add_argument('--conversion', 
                        dest="conv", choices=["EDF","BV","MEEG"], 
                        help="performs conversion to given format")
    return parser.parse_args(argv)
