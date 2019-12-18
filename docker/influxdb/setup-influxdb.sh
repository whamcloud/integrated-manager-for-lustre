#! /bin/sh
apk add curl \
  && [[ $(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 5 --retry 10 --retry-delay 0 http://127.0.0.1:8086/ping) == "204" ]] || false \
  && influx -execute "CREATE DATABASE $INFLUXDB_IML_DB" \
  && influx -execute "CREATE DATABASE $INFLUXDB_STRATAGEM_SCAN_DB"
