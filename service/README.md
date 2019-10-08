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

Each instance generates a log file, which are stored in `s3://manifest.bdrc.org/log/`
## Instance replication
To allow parallel runs, this instance is not generally run. We prepared a launch template for installing it on an
AWS AMI, but this proved too unwieldy to update. A soon-to-be-released version will allow running as a service.

