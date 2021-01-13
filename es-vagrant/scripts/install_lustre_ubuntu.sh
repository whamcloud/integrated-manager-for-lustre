#!/bin/bash

VER=$1

set -e

scp node1:/root/EXAScaler-${VER}/lustre_dgx-${VER}.tar.gz .
tar -axf lustre_dgx-${VER}.tar.gz
cd lustre_dgx-${VER}/lustre-source
# We manually do steps from dgx_install.py
sudo apt-get install -y libtool automake wget git make dpkg-dev bc libselinux-dev ed \
     libssl-dev libreadline-dev debhelper libsnmp-dev \
     rsync libyaml-dev build-essential debhelper devscripts fakeroot \
     kernel-wedge libudev-dev keyutils libkeyutils-dev krb5-multidev \
     libgssapi-krb5-2 libkrb5-3 libkrb5-dev kmod sg3-utils attr lsof \
     pkg-config systemd libelf-dev libtool-bin
./configure --disable-server
make debs
sudo dpkg -i debs/*.deb
