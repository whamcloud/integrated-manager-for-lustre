#!/bin/bash
#
# hydra-host-discover    Chroma host discovery service
#
# chkconfig: 345 88 12
# description: starts the Hydra host discovery daemon
# processname: python

# Source function library.
. /etc/init.d/functions

export SERVICE_NAME=hydra-host-discover
export PROJECT_PATH=/usr/share/hydra-server 

export PYTHONPATH=${PROJECT_PATH}

start() {
    echo -n "Starting the Hydra host discovery daemon: "
    # we don't need --pidfile here since hydra-host-discover is a daemon
    # and takes care of creating the pid file
    daemon /usr/bin/hydra-host-discover
    echo
}

restart() {
    echo -n "Restarting the Hydra host discovery daemon: "
    kill $(cat /var/run/hydra-host-discover.pid)
    # we don't need --pidfile here since hydra-host-discover is a daemon
    # and takes care of creating the pid file
    daemon /usr/bin/hydra-host-discover
    echo
}

stop() {
    echo -n "Stopping hydra-host-discover: "
    kill $(cat /var/run/hydra-host-discover.pid)
    echo
}

case "$1" in
    start)
        start "$2"
        exit $?
        ;;
    stop)
        stop
        exit $?
        ;;
    status)
        # FIXME: check that ALL the pids are running
        status -p /var/run/hydra-host-discover.pid ${SERVICE_NAME}
        exit $?
        ;;

    restart|force-reload)
        restart
        ;;
  *)
        echo "Usage: $0 {start|stop|restart|force-reload}" >&2
        exit 1
        ;;
esac

exit 0
