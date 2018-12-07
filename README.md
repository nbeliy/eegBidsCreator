# eegBidsCreator

A script to convert embla files to the BID standart
It creates the required folders: `sub-<participant_label>/[ses-<session_label>/]eeg`,  which will contain acquisition information, and `source/sub-<participant_label>/[ses-<session_label>/]eeg`, where the original raw data will be copied. If subfolder eeg already exists, the content will be **erased**

It also creates channels.tsv file, containing the list of all channels. Information that I maneged to retrieve are the name, units(may be not accurate), type, description(if it is provided by embla), and sampling frequency. Remaining fields are filled with "n/a".

Extracted events are stored in events.tsv file with its onset time, duration, type, and corresponding sample (i.e. the numero of data point of corresponding time, onset\*sampling) 

I didn't found the task/acquisition/session/run id in the files, so they must be passed to script via options `-t, -a, -s, -r`. Only task option is mandatory.

## Usage

```
usage: eegBidsCreator.py [-h] [-t, --task taskId] [-a, --acquisition acqId]
                         [-s, --session sesId] [-r, --run, runId]
                         [-j, --json eegJson] [-o, --output OUTDIR]
                         [--logfile [log.out]]
                         [--log {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                         [--version]
                         eegfile

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
  --logfile [log.out]   log file destination
  --log {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        logging level
  --version             show program's version number and exit
```

### Example

`python3 eegBidsCreator.py -t my_task "data_example/embla_data/" --log DEBUG`

`python3 eegBidsCreator.py -l task-my_task_eeg.json "data_example/embla_data/" --log DEBUG`

### Dependenties

It runs only with python3, and need following standard modules installed:
- struct (need to convert binary data to various number formats)
- datetime
- sys
- olefile (need to unpack esedb, formatted in ole2)
- argparse
- logging
- argparce
- os
- io
- json
- xml.etree.ElementTree
- glob
- shutil

## Known issues

- Some events don't have an associated type, they will appear as "n/a" in events.tsv file
- For some channels, the names in esedb and in emb files mismach, thus can't determine the corect `sample` value -- **fixed**
- `sample` value can be not an integer, if corresponding event happened between two measures

## Need help!

I have only 3 (now 4, thanks Vinchenzo) embla folders, so my tests are limited. Also I never tested the script on Windows/Mac machine.

So I need maindeuvre for extensive testing on existing data. You can run the script on your embla data, and verify that the retrieved information is correct and it is correctly formatted. 

If there some crash or an infinite loop, please run the script with `--log DEBUG --logfile <your task name>.log` options and send me the resulting file, and if possible the embla files.

Other corrections/suggestions/spell corections can be reported as issues on gitlab. 

## Future plans

- Transform the embla format to brainproducts
- Retrieve and control the information from json file
- Understand the filter and calibration entries
