#!/bin/sh
 set -e

echo "Starting dependency check"

RABBIT_CHECK_URL="http://$AMQP_BROKER_USER:$AMQP_BROKER_PASSWORD@$AMQP_BROKER_HOST:15672/api/aliveness-test/$AMQP_BROKER_VHOST/"

until [ -f /var/lib/chroma/iml-settings.conf ] && psql -h 'postgres' -U 'chroma' -c '\q' && curl -s --fail $RABBIT_CHECK_URL > /dev/null; do
  echo "Waiting for dependencies"
  sleep 5
done
  echo "Dependency check passed"
  exec $@