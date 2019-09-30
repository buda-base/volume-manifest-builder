# volume-manifest-tool
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
- Read input from an S3 device
- Create and save log files.
- Manage input files.

### Standalone tool

Internal tool to create json manifests for volumes present in S3 for the IIIF presentation API server.

#### Dependencies

Python 3.6 or newer.
```
pip3 install pillow boto3 s3transfer
```

# Installation
## Prerequisites
- Python 3.6 or newer
- Install libraries `lxml requests boto3.` `pip3 install lxml requests boto3` will install them. 

- Download [BUDA Github volume-manifest-tool egg](https://github.com/buda-base/volume-manifest-tool/dist/volume-manifest-tool-1.0-py3.6.egg)
- `python3 -m easy_install volume-manifest-tool-1.0-py3.6.egg` This puts the scripts
    - manifestforwork
    - manifestFromS3 
    in your path.  
    **Be sure you are installing under python 3. Use the exact command above.**
- Credentials: you must have the input credentials for a specific AWS user installed to deposit into the archives.

## Building a distribution
Following good practice, we don't distribute the egg above. You can build the distribution by downloading from guthub, and, from the resulting directory:
```bash
python3 setup.py bdist_egg
```
## Usage
### Command line usage
#### Local disk input

Prepare a file listing one RID per line (no `bdr:` prefix), let's say it's on `/path/to/file` and run:

```
./manifestforwork.py /path/to/file
```

#### S3 input
- Upload the input list to [s3://manifest.bdrc.org/processing/todo/](s3://manifest.bdrc.org/processing/todo/)
- run `manifestFromS3` from the command line.

`manifestFromS3` does the following:
1. Moves the desginated input file from `s3://manifest.bdrc.org/processing/input` to `.../processing/inprocess` and changes the name from <input> to <input-instance-id>
2. Runs the processing, uploading a dimensions.json file for each volume in series.
3. When complete, it moves the file from `.../processing/inprocess` to `../processing/done`

The service performs some additional logging and moving, which you can read about in this project's `service/usr/local/bin` folder.

## Service

### Overview

The service version of volume-manifest-tool is intended to be installed in an AWS EC2 AMI where it runs at boot time, and shuts down the machine when completed. If the AWS instance is configured to _terminate on shutdown_ the instance itself will be destroyed. The intent is to create an instance, create a launch template from that instance, containing the image which defines the manifest service, and run through those templated instances, destroying them as needed. This allows massively parallel processing.

### AWS configuration
#### Create an instance
The initial EC2 AMI was an ubuntu 18.04 release (Stretch Debian 9 was considered, but needed work to support Python 3.6) This instance is captured in instance `checkPubImagesUbu (i-0dde090a4aedd0adb)`
Please refer to [Service README.md](service/README.md) for details
You need some AWS credentials in `/etc/buda/volumetool/credentials`, they must allow the user to read all files and write json files in the `archive.tbrc.org` bucket.
#### Install the tools
Installed volume-manifest-tool's prerequisites, and the egg file as above. Included also the necessary AWS identities.
#### Snapshot the instance's attached disk.
You need this for the next step.
#### Create an AMI for the image.
You must have this to create the launch templates. Creating a launch template from an instance does NOT contain the disk bytes of that instance, just the AMI which underlies it. Since we added bits (services and packages) to the AMI, we want those additions to be the basis for any new instances.
When you configure the AMI, use the snapshot you created in the previous step when you configure the AMI's  disk.
#### Create a launch template from the AMI.
Make a note of its id, or search for it. You need this to designate the service to start
#### Testing

Testing is smoother with this knowledge. The service runs
You can launch from a template using a launch template. `aws ec2 run-instances --launch-template LaunchTemplateId=lt-1234567890abcdef`. When you launch this command (using the correct Launch template id) you get back JSON which has the instance-id:

`"InstanceId": "i-04f3e0c7d460e792f"` 

You can then use any tool to monitor the instance. 

If you launch the template, and it has no available input, it terminates the instance. So you would see it in the AWS Console:
![AWS Console](.README_images/AwsConTermImage.png)

If you provide it an input file, it will run while it's processing it. You can validate processing by looking in `s3://manifest.bdrc.org/processing/inprocess`

For example, if you ran this: 

```
aws s3 cp 20190430 s3://manifest.bdrc.org/processing/todo/ && aws ec2 launch-instances --launch-template LaunchTemplateId=lt-0291d00e28fefc2bc
```

and the instance-id which came back from the `ec2 launch-instances` was `i-04f3e0c7d460e792f` you will see the original file and instance name in  `s3://manifest.bdrc.org/processing/` **inprocess/**

```
jimk@Tseng:backlog$ aws s3 ls s3://manifest.bdrc.org/processing/inprocess/
2019-04-30 11:05:38          0
...
2019-05-03 14:38:02         11 20190430-i-04f3e0c7d460e792f
```

You can also monitor the instance in CloudWatch. 

