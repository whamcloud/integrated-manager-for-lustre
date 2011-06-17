#!/bin/bash
#
# hydra-monitor      Starts the hydra monitoring daemon
#
# chkconfig: 345 87 13
# description: starts the Hydra monitoring daemon for the Hydra monitoring \
#    server
# processname: hydra-monitor.py

# Source function library.
. /etc/init.d/functions

test -f /usr/share/hydra-server/monitor/bin/hydra-monitor.py || exit 0

export PYTHONPATH=/usr/share/hydra-server 

start() {
    echo -n "Starting the Hydra monitoring daemon: "
    daemon --pidfile /var/run/hydra-monitor.pid '/usr/share/hydra-server/monitor/bin/hydra-monitor.py >/dev/null & echo "$!" > /var/run/hydra-monitor.pid'
    echo
}

stop() {
    echo -n "Stopping the Hydra monitoring daemon: "
    kill $(cat /var/run/hydra-monitor.pid)
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
