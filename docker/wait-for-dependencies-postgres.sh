#!/bin/bash

set -e

until [ -f /var/lib/chroma/emf-settings.conf ]; do
    echo "Waiting for settings."
    sleep 1
done

TMP=$PROXY_HOST
TMP2=$AMQP_BROKER_HOST
TMP3=$DB_HOST

set -a
source /var/lib/chroma/emf-settings.conf
set +a


if [[ ! -z "$TMP" ]]; then
    export PROXY_HOST=$TMP
fi

if [[ ! -z "$TMP2" ]]; then
    export AMQP_BROKER_HOST=$TMP2
fi

if [[ ! -z "$TMP3" ]]; then
    export DB_HOST=$TMP3
fi

echo "Starting dependency check"

RABBIT_CHECK_URL="http://$AMQP_BROKER_USER:$AMQP_BROKER_PASSWORD@$AMQP_BROKER_HOST:15672/api/aliveness-test/$AMQP_BROKER_VHOST/"

until psql -h 'postgres' -U 'chroma' -c '\q' 2>/dev/null && curl -s --fail $RABBIT_CHECK_URL > /dev/null; do
    echo "Waiting for dependencies"
    sleep 5
done

echo "Dependency check passed"
exec $@