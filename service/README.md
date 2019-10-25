# service
Define a service which launches on startup to run the volume manifest tool
This service is built for a specific AWS AMI running Ubuntu (problems with Python 3.7 on )
## Operating environment
This service installation is built on the `systemctl` platform. The example `default.target` may be different on different Linuces.  On Debian 9, it is `multi-user.target`
You will have to change the `manifest.service` file's  `[Install]` section's `WantedBy` property to match the host platform's target.
## Build instructions
No compilation of the service files is required.
## Installation
1. Copy all the contents of this project's `service` folder  to the target machine. For this example, this will be called `$S_H` (for $SERVICE_HOME). The remaining instructions are arried out on the target machine. 
1. Become super user.
1. Identify the file system that /etc is mounted on. You will need this because the `systemctl enable` command requires the service command files to be on the same partition as the /etc/systemd folder.
1. Create a folder and move the $S_H usr/lib files (manifest.service) there (you dont have to preserve the usr/lib hierarchy. Anywhere is fine.
1. Run `sudo systemctl enable <path to>manifest.service. This should create a link in `/etc/systemd/system/<Install target you picked above>.d/` folder.
1. Create the user `service`, and the following folders:
|||
|----|----|
`~service/tmp`|console log
~service/manifest`|working directory

This configures the system to launch the service on multi-user boot. You can test it
with `sudo systemctl start manifest.service` and look in `~service/tmp/con` for output

should then be able to `systemctl status manifest.service` and start and run it.
 
Manifest Service on boot.

Each instance generates a log file, which are stored in `/var/log/VolumeManifestTool.` make this directory on the target if it does not exist.

