#!/bin/bash
#
# hydra-storage Chroma storage monitoring service
#
# chkconfig: 345 88 12
# description: starts the Hydra storage daemon
# processname: python

. /etc/init.d/functions

export SERVICE_NAME=hydra-storage
export HYDRA_PATH=/usr/share/hydra-server 
export DAEMON_PATH=${HYDRA_PATH}/chroma_core/bin/storage_daemon
export PID_FILE=/var/run/hydra-storage.pid
export LOG_DIR=/var/log/hydra
if ! [ -f ${DAEMON_PATH} ]
then
	echo "Daemon not found at " ${DAEMON_PATH}
	exit -1
fi

export PYTHONPATH=${HYDRA_PATH}

start() {
    action "Starting ${SERVICE_NAME}" daemon --pidfile ${PID_FILE} '${DAEMON_PATH} > ${LOG_DIR}/startup_${SERVICE_NAME}_out.log 2>${LOG_DIR}/startup_${SERVICE_NAME}_err.log & echo $! > ${PID_FILE}'
    echo
}

stop() {
    action "Stopping ${SERVICE_NAME}: " killproc -p ${PID_FILE}
    echo
}

case "$1" in
    start)
        start
        exit $?
        ;;
    stop)
        stop
        exit $?
        ;;
    status)
        status -p ${PID_FILE} ${SERVICE_NAME}
        exit $?
        ;;

    restart|force-reload)
        stop
        start
        exit $?
        ;;
  *)
        echo "Usage: $0 {start|stop|restart|status|force-reload}" >&2
        exit 1
        ;;
esac

exit 0

