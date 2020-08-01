# `volume-manifest-tool`
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
- Read input from an S3 device
- Create and save log files.
- Manage input files.
- Run as a service on a Linux platform

### Standalone tool

Internal tool to create json manifests for volumes present in S3 for the IIIF presentation API server.

#### Dependencies

##### Language
Python 3.6 or newer. It is highly recommended to use `pip` to install, to manage dependencies. If you **must** do it yourself, you can refer to `setup.py` for the dependency list.

##### Environment
1. Write access to `/var/log/VolumeManifestTool` which must exist.
2. `systemctl` service management, if you want to use the existing materials to install as a service.


# Installation
## PIP
PyPI contains `volume-manifest-tool` Install is simply
`sudo python3 -m pip install --upgrade volume-manifest-tool` to install system-wide (which is needed to run as a service)
To install and run locally, `python3 -m pip install --upgrade volume-manifest-tool` will do. 

When you install `volume-manifest-tool` two entry points are defined in `/usr/local/bin`:
- `manifestforwork` the commad mode
- `manifestFromS3` the mode which runs continuously, polling an S3 resource for a file, and processing all the files it finds.
 
## Development
`volume-manifest-tool` is hosted on [BUDA Github volume-manifest-tool](https://github.com/buda-base/volume-manifest-tool/)

- Credentials: you must have the input credentials for a specific AWS user installed to deposit into the archives.

## Building a distribution

Be sure to check PyPI for current release, and update accoringly. Use [PEP440](https://www.python.org/dev/peps/pep-0440/#post-releases) for naming releases.

### Prerequisites
- `pip3 install wheel`
- `pip3 install twine`

```bash
python3 setup.py bdist_wheel
twine upload dist/<thing you built
```
## Usage
`volume-manifest-tool` has two modes:
+ command line, which allows using a list of workRIDS on a local system
+ service, which continually polls a well-known location, `s3://manifest.bdrc.org/processing/todo/` for a file. 

### Command line mode

```
$ manifestforwork -h
usage: manifestforwork sourcefile.

Prepares an inventory of image dimensions

positional arguments:
  sourceFile            File containing one RID per line.

optional arguments:
  -h, --help            show this help message and exit
  -l {info,warning,error,debug,critical}, --loglevel {info,warning,error,debug,critical}
  -i POLL_INTERVAL, --interval POLL_INTERVAL
                        Seconds between alerts for file.
```

Note that `-i` is disregarded in this mode.
#### Local disk input

Prepare a file listing one RID per line (no `bdr:` prefix), let's say it's on `/path/to/file` and run:

```
manifestforwork /path/to/file
```

### S3 input
- Upload the input list to [s3://manifest.bdrc.org/processing/todo/](s3://manifest.bdrc.org/processing/todo/)
- run `manifestFromS3 -i n [ -l {info,debug,error}` from the command line.
See above for argument explanations

`manifestFromS3` does the following:
1. Moves the desginated input file from `s3://manifest.bdrc.org/processing/input` to `.../processing/inprocess` and changes the name from <input> to <input-timestamp-instance-id>
2. Runs the processing, uploading a dimensions.json file for each volume in series.
3. When complete, it moves the file from `.../processing/inprocess` to `../processing/done`
 

### Logging
All messages are output to `/var/log/VolumeManifestTool/`
### Output
`volume-manifest-tool` also probes images for errors, which it writes into its working directory. This functionality largely duplicates other tools, so it is not documented further.
## Service
See [Service Readme](service/README.md) for details on installing manifestFromS3 as a service on `systemctl` supporting platforms.


