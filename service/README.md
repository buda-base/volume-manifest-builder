# service
Define a service which launches on startup to run the volume manifest tool
This service is built for a specific AWS AMI running Ubuntu (problems with Python 3.7 on )
## Operating environment
This service installation is built on the `systemctl` platform.
## Build instructions
No compilation of the service files is required
## Installation
1. Copy all the contents of this project's `service` folder. For this example, this will be called `$S_H` (for $SERVICE_HOME) 
1. ssh to the target machine as someone in the `sudo`group
1. Ensure that the directory `/etc/systemd/system/default.target.wants/` exists. If it does not, you will have to dig into systemctl for your particular system. 
1. Execute these commands in `sudo`
        `sudo ln -s $S_H/usr/lib/systemd/user/manifest.service /etc/systemd/system/default.target.wants`
        
This configures the system to launch the Image Manifest Service on boot.

## Troubleshooting and monitoring.
This code block shows 
1. files being transferred to the well-known address which the image service monitors.
1. Manual instance launch
1. Checking instance state
1. Verifying that the service has moved files from the "inbox" to the "processing" folder. 
1. Verifying that the instance has shut down
1. Verifying that the logs are moved to done.

Each instance generates a log file, which are stored in `s3://manifest.bdrc.org/log/`
## Instance replication
To allow parallel runs, this instance is not generally run. We prepared a launch template ()

