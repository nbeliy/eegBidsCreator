# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [Development]

## [dev0.73] - 2019-04-05

### Fixed
- Forced utf-8 encoding for output files for non-unicode systems
- The end time of a run will no longer crash at second==59
- Forcing delete on outData in case of exception, making it release the output files
- Lack of run label for plugin-defined runs if SlitRuns is deactivated in configuration
- Misspelled name of Embla channel, now class id EmbChannel

### Changed
- `__getvalue__` retrieve now data only within given sequence and becomes `_getValue`
- `__getValueVector__` becomes now `_getValueVector` and retrieves only raw data without oversampling
- `Getvalue` accepts now datetime, timedelta and index parameters to retrieve data points
- `Getvaluevector` accepts date and timedelta to retrieve the data. main algo moved to Generic Channel, and use reimplementation of `_getValueVector` to access data from disk
- `GetIndexTime` now uses `_getLocalIndex` subroutine for index and sequence retrieval
- Streamlined output path treatment and locking mechanism.
- Run now can be only a number
- SetReferenceTime do not recalculate reference times if RefTime is defined and parameter passed is None 

### Added
- A warning if a Calibration function is used in Embla channel
- Set of Channel function to pass from measurement time to local/global indexes and vice-versa
- Several docstrings
- Checks for BIDS compliance in ID labels.
- Virtual static IsBalidInput function to Generic.Record, wich will allow to detect the input format
- InputPath() function to Generic.Record returning the path to input folder
- Embla Record class now inherits from Generic record. All Embla specific functions are moved to DataStructure.Embla.Record
- Added GenRecord.IsValidInput static function. Will return true if input is of a given format
- Added SearchEvent, RSearchEvent SearchEventTime, and RSearchEventTime which implements a search algorithm for an event

## [dev0.72] - 2018-03-07

### Fixed
- Incorrect path for source data
- The call to ch\_dict where this dictionary doesn't exists

### Added 
- An option `[BIDS]OriginalTypes`, which allow to change the original channel types to BIDS accepted ones.
- List of channels triggering a particular event in channels.tsv file

### Changed
- Measurement units prefixes now follows SI as suggested in BIDS, except if conversion is performed into EDF, then prefixes follows EDF+ standard.
- JSON file creation functions are moved to `tools.json`

## [dev0.71] - 2018-03-01

### Fixed
- EventsEP plugin takes now the recording instead of event list
- IncludeSegmentStart now correctly adds new events
- If converted to BV or MEEG, the times in `scans.tsv` are correctly rounded to seconds

### Changed
- `rmdir` becomes rrm and accepts a switch `keepRoot`. If set to `True`, the root directory, passed to `rrm` will be also removed.
- temporary directory now uses only the name of script instead of a full path
- configuration and log files will now be saved at `sourcedata`
- `getValue` and `getValue` will raise `NotImplementedError` is called from Generic/Channel functions
- temporary directory will not have full executable path in its name

### Added
- `participants.json` with `participants.tsv` fields description will be created, if it is missing
- tools.create\_directory function that checks if given directory exists and creates one if not. Also controls if directory contains files needed to be removed.
- `post_processing.py` script which will scan given bids folder, remove duplicates from lists, add headers and clean up files
- Plugin file, if loaded will be saved in `code` directory
- Option `[BIDS]IncludeAuxiliary` to save the auxiliary files in `auxiliaryfiles` folder. This is not BIDS compliant.
- `bidsignore` file that silence the known incompatibilities with bids standard 
- `tools.create_directory` function, that creates directories if these not existing, and checks for files following a pattern inside.

### Removed
- Sample column in `events.tsv`. It is an optional column in any way

## [dev0.7] - 2018-02-27

### Added
- `Examples` folder with some examples, validation and performance scripts
- `doc` folder containing presentations and other documentation
- packed executables for Linux and Windows in `bin` folder
- Anonymization by date and name
- Restriction of memory usage
- Copying of auxiliary files
- If there no conversion, the original embla files are copied to output
- Plugin system
- Conversion to MEEG (SPM12) format
- White and Black lists for channels and events
- Splitting to runs can be now done by sequences, event and its duration or opening and closing events


### Changed
- Exception treatment. Now they are captured and show trace
- Generic functions and parameters reading moved to separate module in `tools` directory
- Rearranged config file and cli parameters

### Fixed
- Events from blacklisted channels will no more produce a warning
- Error if unable to create default temporary directory 
- Wrong sample number for events.tsv
- Lengths restrictions in EDF header
- Duplicated events behaviour in EDF file
- BrainVision '%' symbol incorrect behaviour
- BrainVision event association to channel


### Removed
- Exact times printed out at INFO log level

