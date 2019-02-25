# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

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

