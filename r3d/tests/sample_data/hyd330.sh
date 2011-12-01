#!/bin/sh
set -u -e

MYNAME=$(basename $0 .sh)
RRDTOOL=$HOME/toolkit/lib/rrdtool/rrdtool-1.4.4/src/rrdtool
GENTOOL=$PWD/gen_test_series.py
RRD=$MYNAME.rrd
DATAFILE=$MYNAME.txt
LOGS=logs_$MYNAME
STEP=1
ROWS=50
START=$((1318119548 - $STEP))
END=$((START + ($ROWS * $STEP)))
HEARTBEAT=10

rm -f $DATAFILE
rm -f $RRD
rm -fr $LOGS
mkdir -p $LOGS

$GENTOOL --randslow --randunk --start $((START + $STEP)) --step $STEP --rows $ROWS DS:COUNTER:$HEARTBEAT:U:U DS:GAUGE:$HEARTBEAT:U:U > $DATAFILE

$RRDTOOL create $RRD --step=$STEP --start=$START DS:counter:COUNTER:$HEARTBEAT:U:U DS:gauge:GAUGE:$HEARTBEAT:U:U RRA:AVERAGE:0.5:1:720 > $LOGS/create.log 2>&1

ctr=1
grep -v '\#' $DATAFILE | \
while read line; do
        $RRDTOOL update $RRD $line > $LOGS/$ctr.log 2>&1
        ctr=$((ctr + 1))
done

$RRDTOOL fetch $RRD AVERAGE --start=$((END - ($ROWS / 2))) --end=$END > $LOGS/fetch_step.log 2>&1
