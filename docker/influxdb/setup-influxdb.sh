#! /bin/sh
echo "Creating $INFLUXDB_IML_DB, $INFLUXDB_STRATAGEM_SCAN_DB and $INFLUXDB_IML_STATS_DB databases."
while ! influx -execute "CREATE DATABASE $INFLUXDB_IML_DB" >/dev/null; do
    echo "influx not yet ready"
    sleep 1
done

influx -execute "CREATE DATABASE $INFLUXDB_STRATAGEM_SCAN_DB"
influx -execute "CREATE DATABASE $INFLUXDB_IML_STATS_DB"
