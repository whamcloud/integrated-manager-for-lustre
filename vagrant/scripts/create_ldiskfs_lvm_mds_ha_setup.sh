#!/bin/bash
#
# ARGS: VBOX_USER VBOX_PASSWD VBOX_SSHKEY
#
USER=$1
PASSWD=$2
SSHKEY=$3

pcs cluster auth mds1 mds2 -u hacluster -p lustre
pcs cluster setup --start --name mds-cluster mds1 mds2 --enable --token 17000
pcs stonith create vboxfence fence_vbox ipaddr=10.0.2.2 login=${USER} ${PASSWD:+passwd=${PASSWD}} ${SSHKEY:+identity_file=${SSHKEY}}
pcs resource create mgs-vg ocf:heartbeat:LVM volgrpname=mgt_vg exclusive=true op start timeout=120 op stop timeout=120 --group mgs-grp
pcs resource create mgs ocf:lustre:Lustre target=/dev/mapper/mgt_vg-mgt mountpoint=/mnt/mgs op start timeout=900 op stop timeout=120 --group mgs-grp
pcs resource create mdt0-vg ocf:heartbeat:LVM volgrpname=mdt0_vg exclusive=true op start timeout=120 op stop timeout=120 --group mdt0-grp
pcs resource create mdt0 ocf:lustre:Lustre target=/dev/mapper/mdt0_vg-mdt mountpoint=/mnt/mdt0 op start timeout=900 op stop timeout=120 --group mdt0-grp
pcs resource create mdt1-vg ocf:heartbeat:LVM volgrpname=mdt1_vg exclusive=true op start timeout=120 op stop timeout=120 --group mdt1-grp
pcs resource create mdt1 ocf:lustre:Lustre target=/dev/mapper/mdt1_vg-mdt mountpoint=/mnt/mdt1 op start timeout=900 op stop timeout=120 --group mdt1-grp
