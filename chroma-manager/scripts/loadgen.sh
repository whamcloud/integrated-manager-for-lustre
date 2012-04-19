#!/bin/sh
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================
#
# Usage: 
#   loagen.sh <mount target>
#
# Example:
#   loadgen.sh mgsnode@tcp:/testfs
#

set -xe

if [[ $1 ]]; then
    MGSPATH=$1
    FSNAME=$(basename $MGSPATH)
fi

FSNAME=${FSNAME:-"lustre"}
LUSTRE=${LUSTRE:-"/mnt/client/$FSNAME"}
MGSNID=${MGSNID:-"10.10.0.2@tcp"}
STRIPE_COUNT=${STRIPE_COUNT:=-1}
MGSPATH=${MGSPATH:-$MGSNID:/$FSNAME}

if ! grep -q $LUSTRE /proc/mounts; then
  mkdir -p $LUSTRE
  mount -tlustre $MGSPATH $LUSTRE
#  lfs setstripe $LUSTRE -c $STRIPE_COUNT
fi


while true; do
    name=cptest.$(uname -n)/
    cp -pr /lib/ $LUSTRE/$name
    sleep 1
    rm -rf $LUSTRE/$name

    sleep 1
    name=iotest-$(uname -n)
    lfs setstripe -c $STRIPE_COUNT $LUSTRE/$name
    dd if=/dev/zero of=$name bs=128k count=10k
    rm $name
    sleep $((RANDOM % 100 / 4))
done
