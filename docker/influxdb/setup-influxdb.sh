#! /bin/sh
while ! /usr/bin/pgrep influx >/dev/null; do
    echo "influx not yet ready"
    sleep 1
done

influx -execute "CREATE DATABASE $INFLUXDB_IML_DB"
influx -execute "CREATE DATABASE $INFLUXDB_STRATAGEM_SCAN_DB"
