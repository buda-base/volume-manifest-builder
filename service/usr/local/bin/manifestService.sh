#!/usr/bin/env bash
#
# waits for a status file to appear in a well known location
#
# Requires S3 credentials
#
# Arguments: PID file name
#
# Location:

PID_FILE=${1?"usage $ME pidFileName"}

ME=$(basename $0)
PID_FILE=${1?"usage $ME pidFileName"}

MANIFEST_PROG=/usr/local/bin/manifestFromS3
MyPID=$$

echo $MyPID > $PID_FILE

SERV=$(basename $MANIFEST_PROG)

LOG_DIR=~/manifest/log
S3_LOG_BUCKET=manifest.bdrc.org/log/
S3_ERR_BUCKET=manifest.bdrc.org/errors/

LOG_PATH=${LOG_DIR}/${SERV}.${MyPID}.$(date +%FT%H-%m-%S).log

[[ -d ${LOG_DIR} ]] || { mkdir -p ${LOG_DIR} ;}

echo Manifest service starting $(date)  pid $$ >> $LOG_PATH
$MANIFEST_PROG >> $LOG_PATH 2>&1
aws s3 mv $LOG_PATH s3://${S3_LOG_BUCKET}
aws s3 sync . s3://${S3_ERR_BUCKET} --exclude "*" --include "errors-*" && rm errors-*
#
# jimk: todo: remove these to run locally. these are AWS EC2 constructs
sudo systemctl poweroff
sleep 200

