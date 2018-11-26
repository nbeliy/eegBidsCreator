
These tools reads and extract information from embla-formatted events data (.esedb) and extract the information from it

Contains:
- Parcel, a package for reading embla parcel format
- ewp.py, script for extracting list of events with corresponding timestamps and duration using the same format as wpe.exe
- event_parcer.py, script extracting all possible information from .esedb file and prints it in human format

Python3 dependencies for Parcel module:
- struct (need to convert binary data to various number formats)
- datetime
- sys

Additional dependecies for wpe and event_parcer:
- olefile (need to unpack esedb, formatted in ole2)
- argparse
