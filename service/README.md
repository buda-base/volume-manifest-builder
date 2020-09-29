# service
Define a service which launches on startup to run the volume manifest tool
This service is built for a specific AWS AMI running Ubuntu (problems with Python 3.7 on )
## Operating environment
### Prerequisites
#### OS
* Ubuntu 16.04
* Debian 9 or 10
#### Software
* python 3.7
* volume_manifest_builder installed from pip for the global system. This should include its dependents (boto and others)
#### Service user
Create the user `service`, and the following folders:
|||
|----|----|
`~service/tmp`|console log
`~service/manifest`|working directory
#### Service environment
This service installation is built on the `systemctl` platform. The example `default.target` may be different on different Linuces.  On Debian 9, it is `multi-user.target`
You will have to change the `manifest.service` file's  `[Install]` section's `WantedBy` property to match the host platform's target.
#### Application environment
* User: service
* Folder ~service/volume-manifest-builder
* Folder: /var/log/VolumeManifestBuilder - writable by `service`
* Environment variables required - See [Setting environment variable for service](https://serverfault.com/questions/413397/how-to-set-environment-variable-in-systemd-service). Create and populate these variables:
    * AO_AWS_SNS_TOPIC_ARN

## Build instructions
No compilation of the service files is required.
## Installation
1. Copy all the contents of this project's `service` folder  to the target machine. For this example, this will be called `$S_H` (for $SERVICE_HOME). Follow the remaining instructions on the target machine. 
1. Become super user.
1. Identify the file system that /etc is mounted on. You will need this because the `systemctl enable` command requires the service command files to be on the same partition as the /etc/systemd folder.
1. Create a folder and move the $S_H usr/lib files (manifest.service) there (you dont have to preserve the usr/lib hierarchy. Anywhere is fine, but it should at least not e in your login folder.
1. copy the $S_H/usr/local/bin/v-m-b folder to /usr/local/bin, so that you have /usr/local/bin/v-m-b
1. Run `sudo systemctl enable <path to>manifest.service.` This should create a link in `/etc/systemd/system/<Install target you picked above>.d/` folder.

This configures the system to launch the  /usr/local/bin/manifest-shell.sh on boot.  You can control and monitor the service using strandard `systemctl` commands. 
## Maintenance
To update the Volume Manifest Builder itself, see the installation instructions in the pyPI project
Each instance generates a log file, which are stored in `/var/log/VolumeManifestTool.` make this directory on the target if it does not exist.

