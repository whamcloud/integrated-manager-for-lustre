#!/bin/bash
#
# chroma-worker      Chroma job execution service
#
# chkconfig: 345 87 13
# description: starts the chroma worker daemon (celeryd) 
# processname: python

# Source function library.
. /etc/init.d/functions

export SERVICE_NAME=chroma-worker
export PROJECT_PATH=/usr/share/chroma-manager
export MANAGE_PY=${PROJECT_PATH}/manage.py
export PIDFILE=/var/run/chroma-worker_%n.pid
export LOGFILE=/var/log/chroma/chroma-worker_%n.log
test -f ${MANAGE_PY} || exit 0

export PYTHONPATH=${PROJECT_PATH}
# needed so that ssh can find it's keys
export HOME=/root

# When adding worker, update this and then add args for your worker in run_celeryd
export WORKER_NAMES="serial jobs parselog"

run_celeryd() {
    local op=$1

    python ${MANAGE_PY} celeryd_multi $op ${WORKER_NAMES} -Q:serial periodic,serialize -Q:jobs jobs -Q:parselog parselog -B:serial -c:serial 1 --autoscale:jobs=64,1 --pidfile=$PIDFILE --logfile=$LOGFILE --scheduler=chroma_core.tasks.EphemeralScheduler

}

start() {
    echo -n "Starting ${SERVICE_NAME}: "
    run_celeryd start
    echo
}

restart() {
    echo -n "Restarting ${SERVICE_NAME}: "
    run_celeryd restart
    echo
}

stop() {
    action "Stopping ${SERVICE_NAME}: "python /usr/share/chroma-manager/manage.py celeryd_multi stop ${WORKER_NAMES} --pidfile=$PIDFILE --logfile=$LOGFILE
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
        # FIXME: check that ALL the pids are running
        status -p /var/run/chroma-worker_serial.pid ${SERVICE_NAME}
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
