#!/bin/bash
#
# lustre        This loads the lustre modules
#
# chkconfig: 2345 11 99
# description: This loads the Lustre modules.


PATH=/sbin:/bin:/usr/bin:/usr/sbin

# Source function library.
. /etc/init.d/functions

# Check that we are root ... so non-root users stop here
test $EUID = 0  ||  exit 4

RETVAL=0

start(){
	echo -n "Loading Lustre module stack..."
	/sbin/modprobe lustre
	RETVAL=$?
	echo
	return $RETVAL
}

# See how we were called.
case "$1" in
    start)
	start
	;;
    stop)
	:
	;;
    *)
	echo $"Usage: $0 {start|stop}"
	RETVAL=3
esac

exit $RETVAL
