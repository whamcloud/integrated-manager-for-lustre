#! /bin/sh
apk add curl \
  && timeout -t 300 bash -c 'while [[ "$(curl -s -o /dev/null -w ''%{http_code}'' 127.0.0.1:8086/ping)" != "204" ]]; do echo "Testing influxdb connection" && sleep 5; done' || false \
  && influx -execute "CREATE DATABASE $INFLUXDB_IML_DB" \
  && influx -execute "CREATE DATABASE $INFLUXDB_STRATAGEM_SCAN_DB"
