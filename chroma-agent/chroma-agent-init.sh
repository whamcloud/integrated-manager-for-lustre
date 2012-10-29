#!/bin/bash
#
# chroma-agent Starts the chroma-agent daemon
#
# chkconfig: 345 88 12
# description: Starts the chroma-agent daemon
# processname: python

. /etc/init.d/functions

export SVC_NAME=chroma-agent
export PID_FILE=/var/run/chroma-agent.pid
export DAEMON_BIN=/usr/bin/chroma-agent-daemon

start() {
    echo -n "Starting the Chroma Agent daemon: "
    $DAEMON_BIN --pid-file=$PID_FILE
    echo
}

stop() {
    echo -n "Stopping the Chroma agent daemon: "
    kill $(cat ${PID_FILE})
    echo
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status -p $PID_FILE $SVC_NAME
        exit $?
        ;;
    restart|force-reload)
        stop
        start
        ;;
  *)
        echo "Usage: $0 {start|stop|status|restart|force-reload}" >&2
        exit 1
        ;;
esac

exit 0
