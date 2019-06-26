# eegBidsCreator

A script to convert embla files to the BIDS standard
It creates the required folders: `sub-<participant_label>/[ses-<session_label>/]eeg`,
which will contain acquisition information, and `source/sub-<participant_label>/[ses-<session_label>/]eeg`,
where the original raw data will be copied.

It also creates `channels.tsv` file, containing the list of all channels.
Information that I managed to retrieve are the name, units, type, description (if it is provided by embla),
and sampling frequency. Remaining fields are filled with "n/a".

Extracted events are stored in `events.tsv` file with its onset time, duration, type,
and corresponding sample (i.e. the number of data point of corresponding time, onset\*sampling) 

I didn't found the task/acquisition/session id in the files, so they must be passed to script via options
`-t, -a, -s`. Only task option is mandatory.

If an additional option value `--conversion BV`,`EDF` or `MEEG` is provided, the source files
will be converted into BrainVision/EDF+ format.

## Usage

```
usage: eegBidsCreator.py [-h] [--version] [-a, --acquisition acqId]
                         [-t, --task taskId] [-s, --session sesId]
                         [-j, --json eegJson] [-o, --output OUTDIR]
                         [-c, --config CONFIG_FILE] [--logfile log.out]
                         [-q,--quiet]
                         [--log {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                         [--mem MEM] [--conversion {EDF,BV,MEEG}]
                         eegfile

Converts EEG files to BIDS standard

positional arguments:
  eegfile               input eeg file

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -a, --acquisition acqId
                        Id of the acquisition
  -t, --task taskId     Id of the task
  -s, --session sesId   Id of the session
  -j, --json eegJson    A json file with task description
  -o, --output OUTDIR   destination folder
  -c, --config CONFIG_FILE
                        Path to configuration file
  --logfile log.out     log file destination
  -q,--quiet            Supress standard output
  --log {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        logging level
  --mem MEM             allowed memory usage (in GiB)
  --conversion {EDF,BV,MEEG}
                        performs conversion to given format
```
## BIDS compliency

The created folder structure and file names follows the BIDS standart 1.1.2 with BEP006 addition. 
There are 3 deviations, that I can't fix for now:

 - If choosen to include auxiliary files, they are stored in `auxiliaryfiles` directory in the BIDS root directory. This directory is not under BIDS and will make validator unhappy.
 - The SPM12 MEEG file format is not supported by BIDS at all, and probably will never be.
 - BIDS does not support the storage of events in separated EDF+ file.

These points should be adressed in two ways.
 - In `README` file in root directory, explaining why these files are nessesary.
 - In `.bidsignore` file  in order to silence the validator errors. A working `.bidsignore` can be find in `Example/bidsignore`. Do not foget to add '.' when copying this file.

### Config File

Several options are accessible by the configuration file, which is loaded by `-c <configuration file>`.
The file follows a standard `ini` structure, with parameters and possible values are explained 
in the example file `eegBidsCreator.ini`. 

The parameters specification priority are as follows: `default < conf < cmd line`

**Windows**

Windows in all its glory uses `\n\r` as EOL character. The text files written under the Windows 
are compatible with Nix platforms, but Nix text files are not.

In order to convert one Linux EOL to Windows, one can do in DOS prompt:
```
TYPE input_filename | MORE /P > output_filename
``` 

Another solution is to use a text editor, able to detect the correct EOL characters, like notepad++

### Example

`python3 eegBidsCreator.py -t my_task "data_example/embla_data/" --log DEBUG BrainVision --format INT_16`

`python3 eegBidsCreator.py -t task-my_task_eeg.json "data_example/embla_data/" --log DEBUG`

`python3 eegBidsCreator.py -c eegBidsCreator.conf "data_example/embla_data/" --log DEBUG`

### Dependencies

It runs only with python3, and need following standard modules installed:

 - numpy
 - olefile
 - scipy.io
 - psutil

The next modules are required but seems to be part of python3 standard package:
 - logging
 - os
 - json
 - glob
 - traceback
 - tempfile
 - bisect
 - warnings
 - datetime
 - time
 - importlib.util
 - shutil
 - configparcer
 - argparce
 - struct
 - sys
 - math
 - xml.etree
 - io
 - re

## Stand-alone executables

The stand-alone executables are packed with help of PyInstaller for GNU/Linux and Windows10. They can be found in 
`bin/` directory. Their work was tested on Windows10 and Ubuntu machines, it should be tested on MacOS X and Windows7.

The Python packing is not a true compiling, so the launch of executables takes some time (of order of seconds).
Installing Python and using script directly is still the preferred way to do.

It is not clear how plugin with extra modules will interact with packed version. If one need additional packages within packed executable for satisfying plugin dependencies, he should pack the executable himself.

I use next command line to pack:
```
python3 -m PyInstaller -F --distpath=bin/ eegBidsCreator.py
```

**The executables are guaranteed to correspond to a tagged commit, but I will not do this for each commit between tags**

## Conversion into BrainVision

The original ebmbla format stores each channel into separated file. The values of each measurement points are stored as shorts, with a defined scale (gain) allowing the retrieval of the original value. This system allows to channel to be desynchronized and having independent sampling rate.

The BrainVision format have only one data file, thus all channels must have same sampling rate and to be synchronized.
 
In the conversion, this is achieved by finding the least common multiple for the channels sampling rate (thus all rates should be expressed as integer and measured in `Hz`). If a given channel has a sampling rate lower than the common multiple, then the space between two measurement point is expanded and filled with value of the lower point.

If a given channel has a missing value at given time (i.e. the acquisition started later wrt other channels), they are filled by 0

Finally, the BrainVision format can store the values in float as well as in short with a scale factor. Storage in float remove the need of scale value, but increase size of data file by a factor of 2.

## Conversion into EDF+

The [EDF+ format](https://www.edfplus.info/specs/index.html) contain all channels data in the same file. However, due to the organisation of the data it supports multiple frequencies, so there no need for oversampling. 

The EDF+ format also supports the storage of the events in the same file, but it is difficult to estimate correctly the needed space for the events, so the `eegBidsCreator` stores all the events in separate edf file.

The file is composed of 3 parts: 

- upper block of header, containing a metadata, like subject information, recording information, starting time, duration etc.
- lower block of header, containing description of all channels. In the EDF+ format first channel is reserved for the time stamps of records
- data block, which is organized in records of fixed durations (1 - 10 seconds), containing 2 bit signed short integers as data.

EDF+ supports discontinuous data storage, but it is not yet implemented.
Unlike the BrainVision format, the conversion from short to measured value is not performed via the scale but via the precision of physical and digital extrema. Thus allowing the incorporation of not only a scale of signal but also an offset.

EDF+ supports also encoding of data using logarithmic scale, which is used if the constant relative precision is necessary. As original Embla format works with ranges, this feature wasn't implemented.

## Plugins

Script supported a basic plug-ins. They are activated by giving a path to a py script containing user functions to `[PLUGINS] Plugin` function. Script will load corresponding file and look for following functions:

- `RecordingEP(DataStructure.Generic.Record)`. This one is called just after loading meta-data and before creation of output folders. Allows to modify the metadata, for ex. Acquisition ID, fill JSON information, manipulate subject ID etc.
- `ChannelsEP(list(DataStructure.Generic.Record))`. This one is called after loading list of channels, and allows to manipulate them. List must be manipulated in-place in order to be changed in the main script.
- `EventsEP(list(DataStructure.Generic.Record))`. Called after loading the list of events.
- `RunsEP(list(tuple(datetime,datetime)))`. Called before processing data, and allows the manipulation of runs separation.
- `DataEP(list(DataStructure.Generic.Record), list(list(int/float)))`. Called after loading the data in memory. Allows the manipulation/analysis of given data.

Each of these functions must also accept parameters `cli_args = list(str)` and `cfg_args = list(tuple(str,str))`. The first one is a list of command line options passed after `--`, second is the list of tuples (key, value) representing all parameters in `PLUGINS` section of configuration file.

Each function should return an integer 0, indicating that it was run successfully. Any other returned value will indicate error and will stop execution with code `1xy`, where first digit `1` will indicate that error was produced by plugin, second digit `y` will mark the plugin where error happened (`0 -- RecordingEP`, `1 -- ChannelsEP` etc.), and the last digit `z` will be the same as code returned by plugin. If plugin was stopped by raised exception, `z` digit will be 0.


In order to incorporate printouts of plugin in the logging system, one should include 
```
import logging
Logger = logging.getLogger(__name__)
```
in the beginning of the file. Then use standard `Logging.info/warning/error/debug`.

The Subject, Session, Task, and Acquisition can be changed only at `RecordingEP`, and will be locked afterwards. This is done to fix the output paths.

## Record class definition
It is now possible to define own data reader. For do it, one must create a daughter class of `DataStructure.Generic.Record`, and define in it following functions:

- `@staticmethod _isValidInput(inputPath)` static function that checks if folder given in input path contain a correct data type and return a boolean. This function determines which class will be used to read data
- `__init__(self)` function  that initializes parent and defines associated file extensions 
- `_loadMetadata(self)`, that reads and parses the metadata from source files. It should define subject info with `GenRecord.SetSubject`, device info with `GenRecord.SetDevice`. It could also initialize the recording times with `GenRecord.SetStartTime`
- `_readChannels(self, name=None)` function that reads and defines channels. This function must return a list of readded channels. Channels must inherit from `DataStructure.Generic.Channel`
- `_readEvents(self)` function that reads and defines events. This function must return a list of readded events, that inherits from `DataStructure.Generic.Event`

The channels corresponding the given format must inherit from `DataStructure.Generic.Channel`. 
Channels are supporting discontinuous data. This is implemented via definitions of sequences in two lists: `_seqStartTime` which contains the datetime of the first data point and `_seqSize` which contains number of points of each sequences.
In order to be able to access data, one must define:

- `__init__(self, filename)` functions that initialize the parent class and setup stream
- `_getValue(self, point, sequence)` function that reads and returns value of given index and sequence. It is not expected to check the validity of point and sequence parameters, it is done from interface function `DataStructure.Generic.Channel.GetValue`
- `_getValueVector(self, index, size, sequence)` function that reads and returns a list of data starting at index and of the given size from given sequence. It is expected to stop at the end of sequence.
- `__lt__(self, other)` function that defines `<` less operator used to sort channels.

Channels supports a copy constructor which copies the values of all fields, but preserves the `_getValue` and `_getValueVector` functions of the source channel. So when a data from a copy is acessed, it reads it though the source channel.

## Need help!

**TEST** **TEST** **TEST** 

So I need main d'oeuvre for extensive testing on existing data. You can run the script on your embla data, and verify that the retrieved information is correct and it is correctly formatted. 

If there some crash or an infinite loop, please run the script with `--log DEBUG --logfile <your task name>.log` options and send me the resulting file, and if possible the embla files.

Other corrections/suggestions/spell corrections can be reported as issues on gitlab. 

## Future plans

- Implement version check for ebm
- Understand the filter
- A task given in ini or cli can contain non alphanumeric characters, need to check and produce warning/error
- Treat Frequency correction (how?)
- Transform into C with cpython
- Implement frequency under-sampling
- Implement search and reverse search by event name and time
