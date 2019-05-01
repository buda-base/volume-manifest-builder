#!/usr/bin/env bash

#

SERVICE_NAME=manifestService
SERVICE_SH=${SERVICE_NAME}.sh


PID_FILE=~/tmp/${SERVICE_SH}.pid


function d_start()
{
	echo "${SERVICE_NAME}: starting service"
	/usr/local/bin/${SERVICE_SH} ${PID_FILE}  >> ~/tmp/con 2>&1  &

    echo  "PID is $(cat $PID_FILE)"
}

function d_stop()
{
    if [ -f $PID_FILE ] ; then
        echo "${SERVICE_NAME}: stopping Service (PID = $(cat $PID_FILE))"

        kill "$(cat $PID_FILE)"
    	rm $PID_FILE
    else
        echo "${SERVICE_NAME}: Not running"
    fi
 }

function d_status()
{
	ps  -ef  |  grep ${SERVICE_NAME} |  grep  -v  grep
	echo  "PID indicate indication file $(cat ${PID_FILE}) "
}



# Management instructions of the service
case "$1"  in
	start)
		d_start
		;;
	stop )
		d_stop
		;;
	reload )
		d_stop
		sleep  1
		d_start
		;;
	status )
		d_status
		;;
	* )
	echo  "Usage: $0 {start | stop | reload | status}"
	exit  1
	;;
esac

exit  0