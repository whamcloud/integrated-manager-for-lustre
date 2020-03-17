#! /bin/sh
echo "Creating $INFLUXDB_IML_DB, $INFLUXDB_STRATAGEM_SCAN_DB and $INFLUXDB_IML_STATS_DB databases."
while ! influx -execute "CREATE DATABASE $INFLUXDB_IML_DB" >/dev/null; do
    echo "influx not yet ready"
    sleep 1
done

influx -execute "CREATE DATABASE $INFLUXDB_STRATAGEM_SCAN_DB"
influx -execute "ALTER RETENTION POLICY \"autogen\" ON \"$INFLUXDB_STRATAGEM_SCAN_DB\" DURATION 90d SHARD DURATION 9d"
influx -execute "CREATE DATABASE $INFLUXDB_IML_STATS_DB"
influx -execute "CREATE RETENTION POLICY \"long_term\" ON \"$INFLUXDB_IML_STATS_DB\" DURATION $INFLUXDB_IML_STATS_LONG_DURATION REPLICATION 1 SHARD DURATION 5d" -database $INFLUXDB_IML_STATS_DB
influx -execute "CREATE CONTINUOUS QUERY \"downsample_means\" ON \"$INFLUXDB_IML_STATS_DB\" BEGIN SELECT mean(*) INTO \"$INFLUXDB_IML_STATS_DB\".\"long_term\".:MEASUREMENT FROM \"$INFLUXDB_IML_STATS_DB\".\"autogen\".\"target\",\"$INFLUXDB_IML_STATS_DB\".\"autogen\".\"host\" GROUP BY time(30m),* END; CREATE CONTINUOUS QUERY \"downsample_lnet\" ON \"$INFLUXDB_IML_STATS_DB\" BEGIN SELECT (last(\"send_count\") - first(\"send_count\")) / count(\"send_count\") AS \"mean_diff_send\", (last(\"recv_count\") - first(\"recv_count\")) / count(\"recv_count\") AS \"mean_diff_recv\" INTO \"$INFLUXDB_IML_STATS_DB\".\"long_term\".\"lnet\" FROM \"lnet\" WHERE \"nid\" != '\"0@lo\"' GROUP BY time(30m),\"host\",\"nid\" END; CREATE CONTINUOUS QUERY \"downsample_samples\" ON \"$INFLUXDB_IML_STATS_DB\" BEGIN SELECT (last(\"samples\") - first(\"samples\")) / count(\"samples\") AS \"mean_diff_samples\" INTO \"$INFLUXDB_IML_STATS_DB\".\"long_term\".\"target\" FROM \"target\" GROUP BY time(30m),* END; CREATE CONTINUOUS QUERY \"downsample_sums\" ON \"$INFLUXDB_IML_STATS_DB\" BEGIN SELECT (last(\"sum\") - first(\"sum\")) / count(\"sum\") AS \"mean_diff_sum\" INTO \"$INFLUXDB_IML_STATS_DB\".\"long_term\".\"target\" FROM \"target\" WHERE \"units\"='\"bytes\"' GROUP BY time(30m),* END"
influx -execute "ALTER RETENTION POLICY \"autogen\" ON \"$INFLUXDB_IML_STATS_DB\" DURATION 1d  REPLICATION 1 SHARD DURATION 2h DEFAULT" -database $INFLUXDB_IML_STATS_DB
