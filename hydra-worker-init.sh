#!/bin/bash
#
# hydra-worker      Starts the hydra monitoring daemon
#
# chkconfig: 345 87 13
# description: starts the Hydra worker daemon (celeryd) 
# processname: python

# Source function library.
. /etc/init.d/functions

export PROJECT_PATH=/usr/share/hydra-server 
export MANAGE_PY=${PROJECT_PATH}/manage.py
export PIDFILE=/var/run/hydra-worker_%n.pid
export LOGFILE=/var/log/hydra/hydra-worker_%n.log
test -f ${MANAGE_PY} || exit 0

export PYTHONPATH=${PROJECT_PATH}
# needed so that ssh can find it's keys
export HOME=/root

# When adding worker, update this and then add args for your worker in run_celeryd
export WORKER_NAMES="serial ssh jobs parselog"

run_celeryd() {
    local op=$1

    python ${MANAGE_PY} celeryd_multi $op ${WORKER_NAMES} -Q:serial periodic,serialize -Q:ssh ssh -Q:jobs jobs -Q:parselog parselog -B:serial -c:serial 1 --autoscale:ssh=100,10 --autoscale:jobs=100,10 --pidfile=$PIDFILE --logfile=$LOGFILE

}

start() {
    echo -n "Starting the Hydra worker daemon: "
    run_celeryd start
    echo -n "Starting the Hydra host discovery daemon: "
    # we don't need --pidfile here since hydra-host-discover.py is a daemon
    # and takes care of creating the pid file
    daemon /usr/bin/hydra-host-discover.py
    echo
}

restart() {
    echo -n "Restarting the Hydra worker daemon: "
    run_celeryd restart
    echo -n "Restarting the Hydra host discovery daemon: "
    kill $(cat /var/run/hydra-host-discover.pid)
    # we don't need --pidfile here since hydra-host-discover.py is a daemon
    # and takes care of creating the pid file
    daemon /usr/bin/hydra-host-discover.py
    echo
}

stop() {
    echo -n "Stopping the Hydra host discovery daemon: "
    kill $(cat /var/run/hydra-host-discover.pid)
    echo -n "Stopping the Hydra worker daemon: "
    python /usr/share/hydra-server/manage.py celeryd_multi stop ${WORKER_NAMES} --pidfile=$PIDFILE --logfile=$LOGFILE
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
        restart
        ;;
  *)
        echo "Usage: $0 {start|stop|restart|force-reload}" >&2
        exit 1
        ;;
esac

exit 0
