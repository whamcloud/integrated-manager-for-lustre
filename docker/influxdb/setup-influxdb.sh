#! /bin/sh
echo "Creating $INFLUXDB_IML_DB and $INFLUXDB_STRATAGEM_SCAN_DB databases."
while ! influx -execute "CREATE DATABASE IF NOT EXISTS $INFLUXDB_IML_DB" >/dev/null; do
    echo "influx not yet ready"
    sleep 1
done

influx -execute "CREATE DATABASE IF NOT EXISTS $INFLUXDB_STRATAGEM_SCAN_DB"