#!/bin/sh -xe

# allow caller to override MAPPED_DIR, but default if they don't
MAPPED_DIR="${MAPPED_DIR:-/build}"

# pass the Travis environment into (a file in the) docker environment
env > travis_env

# Run tests in Container
docker run --privileged -d -i -e "container=docker"  -v /sys/fs/cgroup:/sys/fs/cgroup -v "$(pwd)":"$MAPPED_DIR":rw centos:centos7 /usr/sbin/init
DOCKER_CONTAINER_ID=$(docker ps | grep centos | awk 'NR==1{print $1}')
trap 'set -x
docker stop "$DOCKER_CONTAINER_ID"
docker rm -v "$DOCKER_CONTAINER_ID"' EXIT
docker logs "$DOCKER_CONTAINER_ID"
docker exec -i "$DOCKER_CONTAINER_ID" /bin/bash -xec "cd $MAPPED_DIR; $*"
docker ps -a
