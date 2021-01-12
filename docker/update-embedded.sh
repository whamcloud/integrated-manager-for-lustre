#!/bin/sh

export $(sed '/^#/d' /etc/emf-docker/setup/config)

/usr/bin/docker stack deploy -c /etc/emf-docker/docker-compose.yml -c /etc/emf-docker/docker-compose.overrides.yml emf --resolve-image=never