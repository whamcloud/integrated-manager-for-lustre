#!/bin/bash
#
# ARGS: MPATH_LIST IDX VBOX_USER VBOX_PASSWD VBOX_SSHKEY
#
LIST=$1
IDX=$2

USER=$3
PASSWD=$4
SSHKEY=$5

pcs cluster auth oss1 oss2 -u hacluster -p lustre
pcs cluster setup --start --name oss-cluster oss1 oss2 --enable --token 17000
pcs stonith create vboxfence fence_vbox ipaddr=10.0.2.2 login=${USER} ${PASSWD:+passwd=${PASSWD}} ${SSHKEY:+identity_file=${SSHKEY}}

for x in $(eval "echo $LIST"); do
    pcs resource create ost$IDX ocf:lustre:Lustre target=/dev/mapper/mpath$x mountpoint=/mnt/ost$IDX op start timeout=900 op stop timeout=120
    ((IDX++))
done
