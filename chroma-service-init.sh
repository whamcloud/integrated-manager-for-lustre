#!/bin/bash
#
# chroma-service      Starts Chroma service daemon
#
# chkconfig: 345 87 13
# description: starts the Hydra worker daemon (celeryd) 
# processname: python

# Source function library.
. /etc/init.d/functions

export PROJECT_PATH=/usr/share/hydra-server 
export PYTHONPATH=${PROJECT_PATH}
export MANAGE_PY=${PROJECT_PATH}/manage.py
export PIDFILE=/var/run/chroma-service_%n.pid
export LOGFILE=/var/log/hydra/chroma-service_%n.log
export HUMAN_NAME="the Chroma service daemon"
test -f ${MANAGE_PY} || exit 0


export WORKER_NAMES="service"

run_celeryd() {
    local op=$1

    python ${MANAGE_PY} celeryd_multi $op ${WORKER_NAMES} -Q:service service -l:service INFO -c:service 1 --pidfile=$PIDFILE --logfile=$LOGFILE
}

start() {
    echo -n "Starting ${HUMAN_NAME}: "
    run_celeryd start

    # edit /etc/issue to tell where to point the browser
    IPADDR=$(ifconfig | sed -n -e 's/:127\.0\.0\.1 //g' -e 's/ *inet addr:\([0-9.]\+\).*/\1/gp')

    if ! grep "^Please point your browser at" /etc/issue; then
        cat <<EOF >> /etc/issue
Please point your browser at http://$IPADDR/ui/
to administer this server.

EOF
    ui
        ed <<EOF /etc/issue
/^Please point your browser at http:\/\//;/to administer this server\./c
Please point your browser at http://$IPADDR/ui/
to administer this server.
.
w
q
EOF
    fi

    echo

}

restart() {
    echo -n "Restarting ${HUMAN_NAME}: "
    run_celeryd restart
    echo
}

stop() {
    echo -n "Stopping ${HUMAN_NAME}: "
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
