<!-- Required extensions: python-markdown-math -->

# European Data Format + specifications

## Introduction

This describes the EDF+ data format, following the official web page of [EDF+](http://www.edfplus.info/specs/index.html) 

EDF+ is an extension of EDF, with bakward compatibility. It supports event encoding, different sampling rate for channels, continiuos or discontinious data.

## File Composition

In EDF, both meta-data and data are stored in the same `.edf` file. File itself is separated into 3 blocks:
- Upper header, describing general information, subjetc and study id, starting times, number of channels, etc.
- Lower Header, listing all channels with their parametrisations (rate, scaling, description etc.)
- Data block, containing the value of data themself, in the mix of multiplex and paralel organisation.
... The full data taking perioud is separated in shorter **records** of fixed duration $t_r$. For each record the data stored in parallel (first all points of channel 1, then of channel 2 and so on). The records are stored one after another, giving the multiplex aspect.

The exact composition is described below. The bits adresses are given in format `[a:b,c]`, where `a` and `b` are the first and last bits of field, and `c` is the lenght. Positions follows *c++* conventions, the first bit starts at `0`.

### Upper block

Upper block occupies bits `[0:256]` of the edf file. All entries are encoded using standard `US_ASCII` encoding (1 byte per character), with only printable characters are allowed.

Each point describes EDF specification, a sub-point describes additional EDF+ requirement 

- **[0:7,8]** Version of data format, always '0' for EDF/EDF+
- **[8:87,80]** Local patient identification
..- Field composed as follows `<Subject_Code> <Sex:M/F> <Birthdate:dd-MMM-yyyy> <Name>`. Sub-fields are separated by space, all spaces in the sub-fields must be replaced by `_`. If sub-field is unknown, it should be replaced by `X`. Example: `MCH-0234567 F 02-MAY-1951 Haagse_Harry`
- **[88:167,80]** Local recording identification
..- Field composed as follows `Startdate <date:dd-MMM-yyyy> <Inv. code> <Author code> <Material code>`. Sub-fields are separated by space, all spaces in the sub-fields must be replaced by `_`. If sub-field is unknown, it should be replaced by `X`. Example: `Startdate 02-MAR-2002 PSG-1234/2002 NN Telemetry03`
- **[168:175:8]** Start date
..- Format `dd.mm.yy`. Years 85-99 are represent period 1985-1989, and 00-84 represents period 2000-2084
- **[176:183,8]** Start time
..- Format `hh.mm.ss`
- **[184:191,8]** Size of the header (upper block and lower block combined). Value must be equal to $256+256\times{\text{n_c}}$
- **[192:235,44]** Reserved (unused field)
..- EDF+ identifier (`EDF+C` for continous, `EDF+D` for discontinious records)
- **[236:243,8]** Number of data records, `-1` if unknown
- **[244:251,8]** Duration of data record $t_s$, in seconds
- **[252-255,4]** Number of channels in record ($n_c$)

### Lower block

Lower block stores the description of all channels. In case of EDF+, the first channel called *EDF Annotations* will contain the events descriptions and time-stamps. The parameters for channels are grouped together, i.e. First the names of all channels are given, then the types, then scales etc. For this reason only individual field lenghts will be given.

- **$n_c$[16]** Channel label
..- First channel label must be `EDF Annotations`
..- Physical labels are suggested to follow format `<Type> <Specification>`. Howether the list of official types is limited, and not all of them are recognised by analysis software. If there such unrecognized name, then labels will take channel name value. The official labels are given in table...
- **$n_c$[80]** Transducer type
..- There's no standartized way to fill this field, so it could be used as general channel description
- **$n_c$[8]** Physical dimensions, aka Units
..- Units accepts the SI prefixes
..- For official types, the basic measurement units are given in table...
- **$n_c$[8]** Physical minimum, used for signal scaling, see later
- **$n_c$[8]** Physical maximum, used for signal scaling, see later
- **$n_c$[8]** Digital minimum, used for signal scaling, see later. Must be equal or lower than smaller data point
- **$n_c$[8]** Digital maximum, used for signal scaling, see later. Must be equal or bigger than biggest data point
- **$n_c$[80]** Prefiltering
..- Can be used to store the scaling information for very big signal values, see later
- **$n_c$[8]** Number of samples per data record ($n_s$). Related to sampling frequency by $n_s = t_s\times\nu$
- **$n_c$[32]** Reserved (unused)

### Data block

The data block occupies the latter part of the file and serves to store the values of channel as well as time stamps and events (for EDF+ only). It is organized in `data records` of a fixed time duration `$t_s$`. In each data record, the data points are stored parralel, first all the data points from first channel, then from second, etc. Each data point is stored as signed 2-bytes integer, using the little endian order. The signal value ($V$)  and stored value ($V_s$) are related via the following formula:
\[V = \min_\text{ph} + (V_s - \max_\text{ph})\times\frac{\max_\text{ph}-\min_\text{ph}}{\max_\text{dig}-\min_\text{dig}},\]
where $\max_\text{ph}, \min_\text{ph}, \max_\text{dig}, \min_\text{dig} $ are the physical and digital maxima and minima for given channel.








