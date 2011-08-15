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

start() {
    # only on first install...
    #if [ -d /var/lib/mysql/test ]; then
    #    # remove the test database and user from mysqld
    #    /usr/bin/mysql_secure_installation
    #fi
    if [ ! -d /var/lib/mysql/hydra ]; then
        pushd /usr/share/hydra-server
        # create the hydra database
        echo "create database hydra" | mysql
        # and populate it
        PYTHONPATH=$(pwd) python manage.py syncdb --noinput
        popd
    fi

    # RabbitMQ: Configure default hydra user if it's not already set up
    # Note: this would naturally be in %post, but some some build
    # environments run those in the wrong order, so it's here.
    rabbitmqctl list_users | grep "^hydra\\s" > /dev/null || rabbitmqctl add_user hydra hydra123
    rabbitmqctl list_vhosts | grep "^hydravhost$" > /dev/null || rabbitmqctl add_vhost hydravhost
    rabbitmqctl set_permissions -p hydravhost hydra ".*" ".*" ".*"

    echo -n "Starting the Hydra worker daemon: "
    python ${MANAGE_PY} celeryd_multi start serial ssh jobs -Q:serial periodic,serialize -Q:ssh ssh -Q:jobs jobs -B:serial -c:serial 1 --autoscale:ssh=10,100 --autoscale:jobs=10,100 --pidfile=$PIDFILE --logfile=$LOGFILE
    echo
}

restart() {
    echo -n "Restarting the Hydra worker daemon: "
    python ${MANAGE_PY} celeryd_multi restart serial ssh jobs -Q:serial periodic,serialize -Q:ssh ssh -Q:jobs jobs -B:serial -c:serial 1 --autoscale:ssh=10,100 --autoscale:jobs=10,100 --pidfile=$PIDFILE --logfile=$LOGFILE
    echo
}

stop() {
    echo -n "Stopping the Hydra worker daemon: "
    python /usr/share/hydra-server/manage.py celeryd_multi stop serial ssh jobs --pidfile=$PIDFILE --logfile=$LOGFILE
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
