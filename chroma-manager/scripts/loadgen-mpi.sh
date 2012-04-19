#!/bin/sh -xe

if [ "$MPI_HOME" == "" ]; then
  module load openmpi-x86_64
fi

FSNAME=${FSNAME:-"lustre"}
LUSTRE=${LUSTRE:-"/mnt/$FSNAME"}
MGSNID=${MGSNID:-"10.141.255.2@tcp"}
STRIPE_COUNT=${STRIPE_COUNT:=-1}
IOR_SIZE=${IOR_SIZE:-"1G"}

if ! grep -q $LUSTRE /proc/mounts; then
  mkdir -p $LUSTRE
  mount -tlustre $MGSNID:/$FSNAME $LUSTRE
  lfs setstripe $LUSTRE -c $STRIPE_COUNT
fi

while true; do
  simul -d $LUSTRE -n 20 -N 20
  sleep 1
  IOR -b $IOR_SIZE -o $LUSTRE/IOR
  sleep $((RANDOM % 100 / 4))
done
