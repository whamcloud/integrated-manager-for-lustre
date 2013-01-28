#!/bin/bash
#
# chroma-supervisor     Runs supervisord with the Chroma configuration file
#
# chkconfig: 345 88 12
# description: Runs supervisord with the Chroma configuration file
# processname: supervisord

. /etc/init.d/functions

export SERVICE_NAME=chroma-supervisor
export PROJECT_PATH=/usr/share/chroma-manager
export PID_FILE=/var/run/chroma-storage.pid
export LOG_DIR=/var/log/chroma
export PYTHONPATH=${PROJECT_PATH}

start() {
    action "Starting ${SERVICE_NAME}" supervisord --pidfile=${PID_FILE} -c ${PROJECT_PATH}/supervisord.conf -d ${PROJECT_PATH} -l ${LOG_DIR}/supervisord.conf
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

