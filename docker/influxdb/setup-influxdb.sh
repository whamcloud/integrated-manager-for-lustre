#! /bin/sh
/entrypoint.sh influxd &
timeout -t 300 bash -c 'while [[ "$(curl -s -o /dev/null -w ''%{http_code}'' influxdb:8086/ping)" != "204" ]]; do echo "Testing influxdb connection" && sleep 5; done' || false \
  && setup-influxdb \
  && fg

