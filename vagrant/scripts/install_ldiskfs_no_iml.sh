#!/bin/bash

yum-config-manager --add-repo=https://downloads.whamcloud.com/public/lustre/lustre-2.12.3/el7/patchless-ldiskfs-server/
yum-config-manager --add-repo=https://downloads.whamcloud.com/public/e2fsprogs/latest/el7/
yum install -y --nogpgcheck lustre kmod-lustre-osd-ldiskfs
