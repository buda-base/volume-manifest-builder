#!/usr/bin/env bash
#
# waits for a status file to appear in a well known location
#
# Requires S3 credentials
#
# Arguments: PID file name
#
# Location:
ME=$(basename $0)

PID_FILE=${1?"usage $ME pidFileName"}

#
# manifestFromS3 requires Python 3 and pip install
#
MANIFEST_PROG=/usr/local/bin/manifestFromS3
MyPID=$$

echo $MyPID >$PID_FILE

# MANIFEST_PROG now handles logging
# LOG_DIR=~/manifest/log
# S3_LOG_BUCKET=manifest.bdrc.org/log/
# S3_ERR_BUCKET=manifest.bdrc.org/errors/

# LOG_PATH=${LOG_DIR}/${SERV}.${MyPID}.$(date +%FT%H-%m-%S).log

# [[ -d ${LOG_DIR} ]] || { mkdir -p ${LOG_DIR} ;}

$MANIFEST_PROG -l /var/log/VolumeManifestBuilder -d debug -i 600
