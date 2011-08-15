#!/bin/bash
#
# hydra-worker      Starts the hydra monitoring daemon
#
# chkconfig: 345 87 13
# description: starts the Hydra worker daemon (celeryd) 
# processname: python

# Source function library.
. /etc/init.d/functions

export PROJECT_PATH = /usr/share/hydra-server 
export MANAGE_PY = ${PROJECT_PATH}/manage.py
test -f ${MANAGE_PY} || exit 0

export PYTHONPATH=${PROJECT_PATH}

start() {
    echo -n "Starting the Hydra worker daemon: "
    python ${MANAGE_PY} celeryd_multi start serial ssh jobs -Q:serial periodic,serialize -Q:ssh ssh -Q:jobs jobs -c:serial 1 --autoscale:ssh=10,100 --autoscale:jobs=10,100 --pidfile=/var/run/hydra-worker_%n.pid --logfile=./var/log/hydra-worker_%n.log
    echo
}

stop() {
    echo -n "Stopping the Hydra worker daemon: "
    python /usr/share/hydra-server/manage.py celeryd_multi stop serial ssh jobs --pidfile=/var/run/hydra-worker_%n.pid --logfile=./var/log/hydra-worker_%n.log
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
