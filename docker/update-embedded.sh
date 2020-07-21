#!/bin/sh

export $(sed '/^#/d' /etc/iml-docker/setup/config)

/usr/bin/docker stack deploy -c /etc/iml-docker/docker-compose.yml -c /etc/iml-docker/docker-compose.overrides.yml iml --resolve-image=never