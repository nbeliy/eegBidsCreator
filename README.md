# eegBidsCreator

A script to convert embla files to the BID standard
It creates the required folders: `sub-<participant_label>/[ses-<session_label>/]eeg`,  which will contain acquisition information, and `source/sub-<participant_label>/[ses-<session_label>/]eeg`, where the original raw data will be copied. If subfolder eeg already exists, the content will be **erased**

It also creates channels.tsv file, containing the list of all channels. Information that I managed to retrieve are the name, units, type, description (if it is provided by embla), and sampling frequency. Remaining fields are filled with "n/a".

Extracted events are stored in events.tsv file with its onset time, duration, type, and corresponding sample (i.e. the number of data point of corresponding time, onset\*sampling) 

I didn't found the task/acquisition/session/run id in the files, so they must be passed to script via options `-t, -a, -s, -r`. Only task option is mandatory.

If an additional command `BrainVision` or `EDF` is provided, the source files will be converted into BrainVision/EDF+ format.

## Usage

```
usage: eegBidsCreator.py [-h] [-t, --task taskId] [-a, --acquisition acqId]
                         [-s, --session sesId] [-r, --run, runId]
                         [-j, --json eegJson] [-o, --output OUTDIR]
                         [-c, --config [CONFIG_FILE]] [--logfile [log.out]]
                         [-q,--quiet]
                         [--log {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                         [--version]
                         eegfile {BrainVision,EDF} ...

Converts EEG file formats to BID standard

positional arguments:
  eegfile               input eeg file

optional arguments:
  -h, --help            show this help message and exit
  -t, --task taskId     Id of the task
  -a, --acquisition acqId
                        Id of the acquisition
  -s, --session sesId   Id of the session
  -r, --run, runId      Id of the run
  -j, --json eegJson    A json file with task description
  -o, --output OUTDIR   destination folder
  -c, --config [CONFIG_FILE]
                        Path to configuration file
  --logfile [log.out]   log file destination
  -q,--quiet            Supress standard output
  --log {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        logging level
  --version             show program's version number and exit

conversions:
  {BrainVision,EDF}     do <command --help> for additional help
    BrainVision         Conversion to BrainVision format
    EDF                 Conversion to EDF format
```
```
usage: eegBidsCreator.py eegfile BrainVision [-h] [--encoding {UTF-8,ANSI}]
                                             [--format {IEEE_FLOAT_32,INT_16,UINT_16}]
                                             [--big_endian]

optional arguments:
  -h, --help            show this help message and exit
  --encoding {UTF-8,ANSI}
                        Header encoding
  --format {IEEE_FLOAT_32,INT_16,UINT_16}
                        Data number format
  --big_endian          Use big endian
```

### Config File

Several options are accessible by the configuration file, which is loaded by `-c <configuration file>`.
The file follows a standard `ini` structture, with parameters and possible values are explained in the example file `eegBidsCreator.ini`. The parameters specification priority are as follows: `default < conf < cmd line`

### Example

`python3 eegBidsCreator.py -t my_task "data_example/embla_data/" --log DEBUG BrainVision --format INT_16`

`python3 eegBidsCreator.py -t task-my_task_eeg.json "data_example/embla_data/" --log DEBUG`

`python3 eegBidsCreator.py -c eegBidsCreator.conf "data_example/embla_data/" --log DEBUG`

### Dependencies

It runs only with python3, and need following standard modules installed:

- olefile
- json
- glob
- traceback
- struct
- os
- sys
- io
- math
- shutil
- tempfile
- logging
- argparse
- configparser
- datetime
- time


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

- upper block of header, containing a metadata, like subject information, enregistrement information, starting time, duration etc.
- lower block of header, containing description of all channels. In the EDF+ format first channel is reserved for the time stamps of records
- data block, which is organized in records of fixed durations (1 - 10 seconds), containing 2 bit signed short integers as data.

EDF+ supports discontinious data storage, but it is not yet implemented.
Unlike the BrainVision format, the conversion from short to measured value is not performed via the scale but via the precision of physical and digital extrema. Thus allowing the incorporation of not only a scale of signal but also an offset.

EDF+ supports also encoding of data using logaritmic scale, which is used if the constant relative precision is nessesary. As original Embla format works with ranges, this feature wasn't implemented.

## Known issues

- Some events don't have an associated type, they will appear as "n/a" in events.tsv file -- **fixed**
- For some channels, the names in esedb and in emb files mismach, thus can't determine the corect `sample` value -- **fixed**
- `sample` value can be not an integer, if corresponding event happened between two measures -- **fixed**
- Some Embla files contains several events files, need to read all and remove duplicates
- If 2 Emblas treats same subjects, one overrides other, need to fix it
- Interpreting Calibration function produces sometimes a error `eval() arg 1 must be a string, bytes or code object`
- Error `File "DataStructure/Embla/Channel.py", line 209 in _read: b'\xff\xff\xff\xff'`
- Error `"Parcel/parcel.py", line 158 in read: I/O operation on closed file.`

## Need help!

**TEST** **TEST** **TEST** 

So I need maindeuvre for extensive testing on existing data. You can run the script on your embla data, and verify that the retrieved information is correct and it is correctly formatted. 

If there some crash or an infinite loop, please run the script with `--log DEBUG --logfile <your task name>.log` options and send me the resulting file, and if possible the embla files.

Other corrections/suggestions/spell corections can be reported as issues on gitlab. 

## Future plans

- Transform the embla format to brainproducts -- **done**
- Transform the embla format to EDF+ -- **done**
- Implement segmented data
- Implement version check for ebm
- Retrieve and control the information from json file -- **done**
- Understand the filter
- Understand the Calibration -- **done**
- Option to not copy the original data to source
- Log file is appending, make it rotaing/new?
- A task given in ini or cli can contain non alphanumeric characters, need to check and produce warning/error
- Difficult distinguish start of nes bidsifier form end of old
