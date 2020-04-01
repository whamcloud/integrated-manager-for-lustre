#!/bin/bash

START=$1
END=$2
IDX=$3
FSNAME=$4

for x in $(eval echo "{$START..$END}"); do
     mkfs.lustre --ost --reformat --servicenode=10.73.20.21@tcp --servicenode=10.73.20.22@tcp --index=$IDX --mgsnode=10.73.20.11@tcp:10.73.20.12@tcp --fsname=$FSNAME /dev/mapper/mpath$x
     ((IDX++))
done
