#!/bin/bash

yum -y install lvm2
systemctl disable --now lvm2-lvmetad.service lvm2-lvmetad.socket
sed -i -e 's/use_lvmetad = 1/use_lvmetad = 0/' /etc/lvm/lvm.conf

FSNAME=$1
MDT=$2
IDX=$3
MGT=$4

# if doing mdt0 also do mgt
if [ -n "$MGT" ]; then
    pvcreate $MGT
    vgcreate mgt_vg $MGT
    lvcreate -n mgt -l 100%FREE --config activation{volume_list=[\"mgt_vg\"]} --addtag pacemaker mgt_vg
    mkfs.lustre --mgs --reformat --servicenode=10.73.20.11@tcp:10.73.20.12@tcp /dev/mapper/mgt_vg-mgt
fi

pvcreate $MDT
vgcreate mdt${IDX}_vg $MDT
lvcreate -n mdt -l 100%FREE --config activation{volume_list=[\"mdt${IDX}_vg\"]} --addtag pacemaker mdt${IDX}_vg
mkfs.lustre --mdt --reformat --servicenode=10.73.20.11@tcp:10.73.20.12@tcp --index=$IDX --mgsnode=10.73.20.11@tcp:10.73.20.12@tcp --fsname=$FSNAME /dev/mapper/mdt${IDX}_vg-mdt

sed -i -e '/^activation/a\ \tvolume_list = []\n\tauto_activation_volume_list = []' /etc/lvm/lvm.conf
