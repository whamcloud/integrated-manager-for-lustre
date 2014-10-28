#!/bin/bash
#
# chroma-max-clients     Sets MaxClients dependant on system RAM
#
# chkconfig: 345 83 17
# description: Outputs chroma-manager.conf with MaxClients set to total RAM
# processname: python

export PROJECT_PATH=/usr/share/chroma-manager
export CONF_PATH=/etc/httpd/conf.d
export PYTHONPATH=${PROJECT_PATH}

# Source function library.
. /etc/init.d/functions

start() {
    echo "Updating MaxClients"
    python ${PROJECT_PATH}/scripts/production_httpd.pyc \
    ${PROJECT_PATH}/chroma-manager.conf.template > ${CONF_PATH}/chroma-manager.conf
    echo
}

case "$1" in
    start)
        start
        exit $?
        ;;
    status)
        sed -n '/MaxClients [[:digit:]]/p' ${CONF_PATH}/chroma-manager.conf
        echo
        exit $?
        ;;
  *)
        echo "Usage: $0 {start|status}" >&2
        exit 1
        ;;
esac

exit 0