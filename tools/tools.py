############################################################################# 
## tools contains a set of folder and files manipulation routines
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



import os
import shutil
import glob
import logging

Logger = logging.getLogger(__name__)


def rrm(path, keepRoot=False):
    '''Recursive remove of files and directories 
    under given path. If keepRoot is True, the 
    doesn't remove the path.'''
    if os.path.isfile(path):
        os.remove(path)
    else:
        for root, dirs, files in os.walk(path):
            for f in files:
                os.remove(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))
            if not keepRoot:
                shutil.rmtree(root)


def humanbytes(B):
    '''Return the given bytes as a human friendly KB, MB, GB, or TB string'''
    B = float(B)
    KB = float(1024)
    MB = float(KB ** 2)  # 1,048,576
    GB = float(KB ** 3)  # 1,073,741,824
    TB = float(KB ** 4)  # 1,099,511,627,776

    if B < KB:
        return '{0} {1}'.format(B,'Bytes' if 0 == B > 1 else 'Byte')
    elif KB <= B < MB:
        return '{0:.2f} KB'.format(B / KB)
    elif MB <= B < GB:
        return '{0:.2f} MB'.format(B / MB)
    elif GB <= B < TB:
        return '{0:.2f} GB'.format(B / GB)
    elif TB <= B:
        return '{0:.2f} TB'.format(B / TB)


def create_directory(path, toRemove="", allowDups=True):
    """Checks if given path exists, and is a directory.
    If create is True and path not exists, a directory will be created.
    If toRemove is not '', will control if files with this name exist. 
    If allowDups is True, such files will be removed. If
    allowDups is False, an exception will be raised"""
    if path[-1] != '/':
        path += '/'
    res = os.path.isdir(path)
    if not res and os.path.isfile(path):
        raise NotADirectoryError("{} is a file".format(path))
    if not res:
        Logger.info("Creating directory {}".format(path))
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
    else:
        Logger.debug("Directory {} exists".format(path))
        if toRemove != "":
            flist = glob.glob(path + toRemove)
            if flist != []:
                msg = "Found {} files with pattern '{}'."\
                      .format(len(flist), toRemove)
                if allowDups:
                    Logger.warning(msg)
                    Logger.warning("They will be removed.")
                    for f in flist:
                        rrm(f)
                else:
                    raise FileExistsError(msg + "Please remove them.")


def remove_empty_dir(path):
    try:
        os.rmdir(path)
        Logger.info("Removed empty directory {}".format(path))
    except OSError:
        pass


def remove_empty_dirs(path):
    for root, dirnames, filenames in os.walk(path, topdown=False):
        for dirname in dirnames:
            remove_empty_dir(os.path.realpath(os.path.join(root, dirname)))
