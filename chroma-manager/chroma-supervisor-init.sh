#!/bin/bash
#
# chroma-storage Chroma storage monitoring service
#
# chkconfig: 345 88 12
# description: starts the chroma storage daemon
# processname: python

. /etc/init.d/functions

export SERVICE_NAME=chroma-supervisor
export PROJECT_PATH=/usr/share/chroma-manager
export PID_FILE=/var/run/chroma-storage.pid
export LOG_DIR=/var/log/chroma
export PYTHONPATH=${PROJECT_PATH}

start() {
    action "Starting ${SERVICE_NAME}"  python ${PROJECT_PATH}/manage.py chroma_service --daemon --pid-file=${PID_FILE} job_scheduler plugin_runner
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

