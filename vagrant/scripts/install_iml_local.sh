#!/bin/bash

yum copr enable -y managerforlustre/manager-for-lustre-devel
yum install -y rpmdevtools git ed epel-release python-setuptools gcc openssl-devel
curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env
cd /integrated-manager-for-lustre
make copr-rpms

mkdir -p /tmp/{manager,agent}-rpms
cp /integrated-manager-for-lustre/_topdir/RPMS/x86_64/rust-iml-{action-runner,cli,ostpool,stratagem,agent-comms,mailbox,warp-drive}-*.rpm /tmp/manager-rpms/
cp /integrated-manager-for-lustre/_topdir/RPMS/x86_64/rust-iml-agent-[0-9]*.rpm /tmp/agent-rpms
make rpms
cp /integrated-manager-for-lustre/_topdir/RPMS/noarch/python2-iml-manager-* /tmp/manager-rpms/

cp /integrated-manager-for-lustre/chroma_support.repo /etc/yum.repos.d/
yum localinstall -y /tmp/manager-rpms/*.rpm

chroma-config setup admin lustre localhost --no-dbspace-check
