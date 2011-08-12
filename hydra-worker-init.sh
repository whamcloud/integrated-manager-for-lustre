#!/bin/bash
#
# hydra-worker      Starts the hydra monitoring daemon
#
# chkconfig: 345 87 13
# description: starts the Hydra worker daemon (celeryd) 
# processname: python

# Source function library.
. /etc/init.d/functions

test -f /usr/share/hydra-server/manage.py || exit 0

export PYTHONPATH=/usr/share/hydra-server 

start() {
    # only on first install...
    #if [ -d /var/lib/mysql/test ]; then
    #    # remove the test database and user from mysqld
    #    /usr/bin/mysql_secure_installation
    #fi
    if [ ! -d /var/lib/mysql/hydra ]; then
        pushd /usr/share/hydra-server
        # create the hydra database
        #PYTHONPATH=$(pwd) python manage.py dbshell << EOF
#create database hydra
#EOF
        echo "create database hydra" | mysql
        # and populate it
        PYTHONPATH=$(pwd) python manage.py syncdb --noinput
        popd
    fi

    echo -n "Starting the Hydra worker daemon: "
    daemon --pidfile /var/run/hydra-worker.pid 'python /usr/share/hydra-server/manage.py celeryd --logfile=/var/log/celery.log -B -c 10 2>&1 > /dev/null & echo "$!" > /var/run/hydra-worker.pid'
    echo
}

stop() {
    echo -n "Stopping the Hydra worker daemon: "
    kill $(cat /var/run/hydra-worker.pid)
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
