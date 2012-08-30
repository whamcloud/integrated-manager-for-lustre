#!/bin/sh

# hate to hard-code these, but whatevs
RABBITMQ_USER="chroma"
RABBITMQ_PASSWORD="chroma123"
RABBITMQ_VHOST="chromavhost"
MQCTL=rabbitmqctl

if ! grep -q $RABBITMQ_USER <($MQCTL -q list_users); then
    $MQCTL add_user $RABBITMQ_USER $RABBITMQ_PASSWORD
fi

if ! grep -q $RABBITMQ_VHOST <($MQCTL -q list_vhosts); then
    $MQCTL add_vhost $RABBITMQ_VHOST
fi

$MQCTL set_permissions -p $RABBITMQ_VHOST $RABBITMQ_USER ".*" ".*" ".*"
