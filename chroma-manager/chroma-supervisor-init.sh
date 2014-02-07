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
export PID_FILE=/var/run/chroma-supervisor.pid
export LOG_DIR=/var/log/chroma
export PYTHONPATH=${PROJECT_PATH}
export SUPERVISOR_CONFIG=${PROJECT_PATH}/production_supervisord.conf


start() {
    if [ -f $PID_FILE ] ; then
        ps -p `cat $PID_FILE` > /dev/null 2>&1
        if [ "$?" = 0 ] ; then
            echo "Already running"
            exit 0
        fi
    fi
    action "Starting ${SERVICE_NAME}" supervisord --pidfile=${PID_FILE} -c ${SUPERVISOR_CONFIG} -d ${PROJECT_PATH} -e debug -l ${LOG_DIR}/supervisord.log
    echo
}

graceful_stop() {
    # Use -TERM to prevent killproc -KILL'ing supervisord when it doesn't
    # exit immediately: that would orphan supervisor's children.
    (killproc -p ${PID_FILE} ${SERVICE_NAME} -TERM) > /dev/null

    #  Kill proc does wait for services to stop before removing pid, but it doesn't block.
    #  Wait here and watch that pid through status calls.  It's one when status says so.
    SECONDS=0
    while [ $SECONDS -lt 60 ]; do
        status -p ${PID_FILE} ${SERVICE_NAME} > /dev/null 2>&1
        if [ $? -eq 3 ]; then
            return 0  #  Stopped cleanly
        fi
        echo -n '.'
        sleep 2
    done
    return 124 # did not stop, or did not stop cleanly
}

stop() {
    action "Stopping ${SERVICE_NAME}: " graceful_stop
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

