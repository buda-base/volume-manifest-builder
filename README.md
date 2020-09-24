# `bdrc-volume-manifest-builder`
## New in Release 1.1
- Ability to use either file system or S3 for image repository
## Intent
This project originated as a script to extract image dimensions from a work, and:
+ write the dimensions to a json file
+ report on images which broke certain rules.
## Implementation
Archival Operations determined that this would be most useful to BUDA to implement as a service which could be injected into the current sync process. To do this, the system needed to:
- be more modular
- be distributable onto an instance which could be cloned in AWS.

This branch expands the original tool by:
- Adding the ability to use the eXist db as a source for the image dimensions.
- Use a pre-built BOM Bill of Materials) to derive the files which should be included in the dimesnsions file
- Read input from either S3 or local file system repositories
- Create and save log files.
- Manage input files.
- Run as a service on a Linux platform

### Standalone tool

Internal tool to create json manifests of image format data for volumes present in S3 to support the BUDA IIIF
presentation server.

##### Language
Python 3.7 or newer. It is highly recommended to use `pip` to install, to manage dependencies. If you **must** do it
yourself, you can refer to `setup.py` for the dependency list.

##### Environment
1. Write access to `/var/log/VolumeManifestBuilder` which must exist.
2. `systemctl` service management, if you want to use the existing materials to install as a service.

## Usage
### Command line usage
The command line mode allows running one batch or one work at a time. Arguments
specify the parameters, options.

You also must choose a **repository mode** which determines if the images
are on a local file system (the `fs` mode), or on an AWS S3 system (the `s3`)
mode.
#### Common parameters
This section describes the parameters which are independent of the repository mode.
```shell script
$ manifestforwork -h
usage: manifestforwork [common options] { fs [fs options] | s3 [s3 options]}

Prepares an inventory of image dimensions

optional arguments:
  -h, --help            show this help message and exit
  -d {info,warning,error,debug,critical}, --debugLevel {info,warning,error,debug,critical}
                        choice values are from python logging module
  -l LOG_PARENT, --logDir LOG_PARENT
                        Path to log file directory
  -f WORK_LIST_FILE, --workListFile WORK_LIST_FILE
                        File containing one RID per line.
  -w WORK_RID, --work-Rid WORK_RID
                        name or partially qualified path to one work
  -p POLL_INTERVAL, --poll-interval POLL_INTERVAL
                        Seconds between alerts for file.

Repository Parser:
  Handles repository alternatives


  {s3,fs}

```
Common usage Notes:

`-f/--workListFile` is a file which contains a list of RIDS, **or a list of paths
to work RIDs, in the `fs` mode (see below.)**
`-w/--workRID` is a single work.

- The `--workListFile` and `--workRid` arguments are mutually exclusive  

- `-p` is disregarded in this mode. It is an argument to the `manifestFromS3`
- The system logs its activity into a file named _yyyy-MM-DD_HH_MM_PID_.local_v_m_b.log`
in the folder given in the `-l/--logDir` argument (default `/var/log`)
mode.

#### fs Mode Usage
```shell script
❯ manifestforwork fs -h
usage: manifestforwork [common options] { fs [fs options] | s3 [s3 options]} fs
       [-h] [-c CONTAINER] [-i IMAGE_FOLDER_NAME]

optional arguments:
  -h, --help            show this help message and exit
  -c CONTAINER, --container CONTAINER
                        container for all work_Rid archives. Prefixes entries
                        in --source_rid or --workList
  -i IMAGE_FOLDER_NAME, --image-folder-name IMAGE_FOLDER_NAME
                        name of parent folder of image files
```

Notes:
+ the `-c/--container` defines a path to the RIDS (or the RID subpaths) given.
It is optional. It prepends its value to the WorkRID paths or individual workRIDs
in the input file (`-f`) or to the individual work (`-w`)

In the `-w` or `-f` options above. The system supports user expansion
(`~[uid]/path...` in Linux) and environment variable expansion in both the `-c`
and the `-f` options. That is, the file given in the `-f` option can contain
  - Environment variables
  - User alias pathnames (`~[user]/...`)
  - Fully qualified pathnames

e.g.
```shell script
> pwd
/data
>ls
Works
>ls ~/tmp
/home/me/tmp/Works
> export THISWORK="Works/FromThom"
> cat workList
$WORKS/W12345
~/tmp/$WORKS/W12345
/home/me/tmp/Works/W89012
```
using this list in

```shell script
> manifestforwork -f worklist fs
```
will process files from
 - /data/Works/FromThom
 - /home/me/tmp/Works/FromThom
 - /home/me/tmp/Works/W89012
 if the `--container` argument is not given. (`-c` defaults to the current working 
 directory)
 
#### s3 mode usage

```shell script
❯ manifestforwork s3 --help
usage: manifestforwork [common options] { fs [fs options] | s3 [s3 options]} s3
       [-h] [-b BUCKET]

optional arguments:
  -h, --help            show this help message and exit
  -b BUCKET, --bucket BUCKET
                        Bucket - source and destination
```
The S3 mode uses a bucket named with the optional `-b/--bucket` argument. The default bucket
is closely held. note that the `--container` argument is not applicable in this mode, and
that if a worklist is given, it must contain only RIDs, not paths.


### manifestFromS3 input

`manifestFromS3` is a mode which waits for a list of RIDs or paths to appear in a well known location
and then processes what it finds there as if it were given in the `--workFile` argument.

All the other parameters are the same - `manifestFromS3` can work on local file system (`fs`)
or on `s3` targets.

- Upload an input list (file name does not matter) to [s3://manifest.bdrc.org/processing/todo/](s3://manifest.bdrc.org/processing/todo/)
- run `manifestFromS3 -p n [ -l {info,debug,error}  {fs [ fs arguments ] | s3 [ -b alternative.bucket]}` 
from the command line.

`manifestFromS3` does the following:
1. Moves the input list from `s3://manifest.bdrc.org/processing/input` to `.../processing/inprocess` and changes the name from <input> to <input-timestamp-instance-id>
2. Runs the processing, uploading a dimensions.json file for each volume in each 
RID in the input list.
3. When complete, it moves the file from `.../processing/inprocess` to `../processing/done`
## Installation
### PIP
PyPI contains `bdrc-volume-manifest-builder`
#### Global installation
Install is simply
`sudo python3 -m pip install --upgrade bdrc-volume-manifest-builder` to install system-wide (which is needed to run as a service)
#### Local installation
To install and run locally, `python3 -m pip install --upgrade bdrc-volume-manifest-builder` will do. Best to do this in
a virtual python environment, see [venv](https://docs.python.org/3/library/venv.html)

When you install `volume-manifest-builder` three entry points are defined in `/usr/local/bin` (or your local environment):
- `manifestforlist` the command mode, which operates on a list of RIDs
- `manifestforwork` alternate command line mode, which works on one path
- `manifestFromS3` the mode which runs continuously, polling an S3 resource for a file, and processing all the files it finds.
This is the mode which runs on a service.
## Service
See [Service Readme](service/README.md) for details on installing manifestFromS3 as a service on `systemctl` supporting platforms.



## Development
`volume-manifest-builder` is hosted on [BUDA Github volume-manifest-builder](https://github.com/buda-base/volume-manifest-builder/)

- Credentials: you must have the input credentials for a specific AWS user installed to deposit into the archives on s3.

## Usage
`volume-manifest-builder` has two use cases:
+ command line, which allows using a list of workRIDS on a local system
+ service, which continually polls a well-known location, `s3://manifest.bdrc.org/processing/todo/` for a file.

## Building a distribution

Be sure to check PyPI for current release, and update accordingly. Use [PEP440](https://www.python.org/dev/peps/pep-0440/#post-releases) for naming releases.

### Prerequisites
- `pip3 install wheel`
- `pip3 install twine`

```bash
python3 setup.py bdist_wheel
twine upload dist/<thing you built
```
