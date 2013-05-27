#!/bin/sh
#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.
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
LUSTRE=${LUSTRE:-"/mnt/client/$FSNAME"}
MGSNID=${MGSNID:-"10.10.0.2@tcp"}
STRIPE_COUNT=${STRIPE_COUNT:=-1}
MGSPATH=${MGSPATH:-$MGSNID:/$FSNAME}

if ! grep -q $LUSTRE /proc/mounts; then
  mkdir -p $LUSTRE
  mount -tlustre $MGSPATH $LUSTRE
#  lfs setstripe $LUSTRE -c $STRIPE_COUNT
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
