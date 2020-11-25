#!/usr/bin/env bash
set -eux
/bin/mkdir -p /etc/iml
service=iml_influxdb
trailer=$(/usr/bin/docker service ps -f "name=$service.1" $service -q --no-trunc | head -n1)
until /usr/bin/docker exec $service.1.$trailer /bin/bash -c 'until [ -f /var/lib/chroma/iml-settings.conf ]; do echo "Waiting for settings."; sleep 1; done'; do
  echo "Waiting for container"
  sleep 1
done
/usr/bin/docker cp $service.1.$trailer:/var/lib/chroma/iml-settings.conf /etc/iml/iml-settings.conf
