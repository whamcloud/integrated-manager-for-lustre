#!/bin/bash
#
# hydra-storage Starts the hydra monitoring daemon
#
# chkconfig: 345 87 13
# description: starts the Hydra storage daemon
# processname: python

. /etc/init.d/functions

export HYDRA_PATH=/usr/share/hydra-server 
export DAEMON_PATH=${HYDRA_PATH}/configure/bin/storage_daemon
export PID_FILE=/var/run/hydra-storage.pid
if ! [ -f ${DAEMON_PATH} ]
then
	echo "Daemon not found at " ${DAEMON_PATH}
	exit -1
fi

export PYTHONPATH=${HYDRA_PATH}

start() {
    echo -n "Starting the Hydra storage daemon: "
    daemon --pidfile ${PID_FILE} '${DAEMON_PATH} >/dev/null & echo "$!" > ${PID_FILE}'
    echo
}

stop() {
    echo -n "Stopping the Hydra storage daemon: "
    kill `cat ${PID_FILE}`
    echo
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;

    restart|force-reload)
        stop
        start
        ;;
  *)
        echo "Usage: $0 {start|stop|restart|force-reload}" >&2
        exit 1
        ;;
esac

exit 0

