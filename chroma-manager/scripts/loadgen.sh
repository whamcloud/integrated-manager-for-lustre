#!/bin/sh
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================
#
# Usage: 
#   loagen.sh <mount target> [mntpoint]
#
# Examples:
#   loadgen.sh mgsnode@tcp:/testfs
#   loadgen.sh mgsnode@tcp:/testfs mount2
#

set -xe

if [[ $1 ]]; then
    MGSPATH=$1
    FSNAME=$(basename $MGSPATH)
fi

if [[ $2 ]]; then
    FSNAME=$2
fi

FSNAME=${FSNAME:-"lustre"}
LUSTRE_BASE=${LUSTRE:-"/mnt/client/$FSNAME"}
MGSNID=${MGSNID:-"10.10.0.2@tcp"}
STRIPE_COUNT=${STRIPE_COUNT:=-1}
MGSPATH=${MGSPATH:-$MGSNID:/$FSNAME}
THREADS=${THREADS:=1}

for ((thread=1; $thread <= $THREADS; thread++)); do
(
    if [ $THREADS -gt 1 ]; then
        LUSTRE="$LUSTRE_BASE-$thread"
    else
        LUSTRE="$LUSTRE_BASE"
    fi
    if ! grep -q $LUSTRE /proc/mounts; then
        mkdir -p $LUSTRE
        while ! mount -tlustre $MGSPATH $LUSTRE; do
            echo "failed to mount.  trying again in a sec..."
            sleep 1
        done
        #lfs setstripe $LUSTRE -c $STRIPE_COUNT
    else
        MGSPATH=$(grep $LUSTRE /proc/mounts | sed -e 's/ .*//')
    fi
    
    
    while true; do
        name=$LUSTRE/cptest.$(uname -n)/
        cp -pr /lib/ $name
        sleep 1
        rm -rf $name
    
        sleep 1
        name=$LUSTRE/iotest-$(uname -n)
        rm -f $name
        lfs setstripe -c $STRIPE_COUNT $name
        dd if=/dev/zero of=$name bs=128k count=10k
        umount $LUSTRE
        while ! mount -tlustre $MGSPATH $LUSTRE; do
            echo "failed to mount.  trying again in a sec..."
            sleep 1
        done
        dd of=/dev/zero if=$name bs=128k count=10k
        rm -f $name
        sleep $((RANDOM % 100 / 4))
    done
) &
done

wait
