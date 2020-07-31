#!/bin/bash

LUSTRE=$1

yum-config-manager --add-repo=https://downloads.whamcloud.com/public/lustre/lustre-$LUSTRE/el7/patchless-ldiskfs-server/
yum-config-manager --add-repo=https://downloads.whamcloud.com/public/e2fsprogs/latest/el7/
yum-config-manager --add-repo=http://download.zfsonlinux.org/epel/7.6/kmod/x86_64/
yum install -y --nogpgcheck lustre zfs kmod-lustre-osd-ldiskfs kmod-lustre-osd-zfs
systemctl enable --now zfs-zed
