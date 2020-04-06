#!/bin/bash

LUSTRE=$1

yum-config-manager --add-repo=https://downloads.whamcloud.com/public/lustre/lustre-$LUSTRE/el7/patchless-ldiskfs-server/
yum-config-manager --add-repo=https://downloads.whamcloud.com/public/e2fsprogs/latest/el7/
yum install -y --nogpgcheck lustre kmod-lustre-osd-ldiskfs
