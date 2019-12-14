#! /bin/sh
/entrypoint.sh influxd \
  && timeout -t 60 bash -c 'while [[ "$(curl -s -o /dev/null -w ''%{http_code}'' influxdb:8086/ping)" != "201" ]]; do echo "Testing influxdb connection" && sleep 5; done' || false \
  && setup-influxdb

