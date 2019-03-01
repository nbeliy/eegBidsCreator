# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [Developpement]

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
- plugin file, if loaded will be saved in `code` directory
- Option `[BIDS]IncludeAuxiliary` to save the auxiliery files in `auxiliaryfiles` folder. This is not BIDS compolient.
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
- Copying of auxiliery files
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
- Lenghts restrictions in EDF header
- Duplicated events behaviour in EDF file
- BrainVision '%' symbol uncorrect behaviour
- BrainVision event association to channel


### Removed
- Exact times printed out at INFO log level

