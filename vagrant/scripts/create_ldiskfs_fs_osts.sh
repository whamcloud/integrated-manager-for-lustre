#!/bin/bash

START=$1
END=$2
IDX=$3
FSNAME=$4
MGT=$5

if [ -n "$MGT" ]; then
    pvcreate $MGT
    vgcreate mgt2_vg $MGT
    lvcreate -n mgt2 -l 100%FREE --config activation{volume_list=[\"mgt2_vg\"]} --addtag pacemaker mgt2_vg
    mkfs.lustre --mgs --reformat --servicenode=10.73.20.21@tcp:10.73.20.22@tcp /dev/mapper/mgt2_vg-mgt2
fi

for x in $(eval echo "{$START..$END}"); do
     mkfs.lustre --ost --reformat --servicenode=10.73.20.21@tcp --servicenode=10.73.20.22@tcp --index=$IDX --mgsnode=10.73.20.11@tcp:10.73.20.12@tcp --fsname=$FSNAME /dev/mapper/mpath$x
     ((IDX++))
done
