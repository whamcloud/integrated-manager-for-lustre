#!/bin/bash

yum copr enable -y managerforlustre/manager-for-lustre-devel
yum install -y rpmdevtools git ed epel-release python-setuptools gcc openssl-devel
curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env
cd /integrated-manager-for-lustre

# Bump the release number. This should ensure we get picked 
#even if copr-devel has something newer
rpmdev-bumpspec rust-iml.spec
rpmdev-bumpspec python-iml-manager.spec

# Use current timestamp to ensure running this again
# causes a re-install
TS=$(date +%s)

V=$(rpmspec -q --srpm --queryformat='%{VERSION}' /integrated-manager-for-lustre/rust-iml.spec)
rpmdev-bumpspec -n $V.$TS rust-iml.spec

V=$(rpmspec -q --srpm --queryformat='%{VERSION}' /integrated-manager-for-lustre/python-iml-manager.spec)
rpmdev-bumpspec -n $V.$TS python-iml-manager.spec

make all

rm -rf /tmp/{manager,agent}-rpms
mkdir -p /tmp/{manager,agent}-rpms

cp /integrated-manager-for-lustre/_topdir/RPMS/x86_64/rust-iml-{action-runner,cli,ostpool,stratagem,agent-comms,mailbox,warp-drive}-*.rpm,python2-iml-manager-* /tmp/manager-rpms/
cp /integrated-manager-for-lustre/_topdir/RPMS/x86_64/rust-iml-agent-[0-9]*.rpm /tmp/agent-rpms
cp /integrated-manager-for-lustre/chroma_support.repo /etc/yum.repos.d/

yum install -y /tmp/manager-rpms/*.rpm

chroma-config setup admin lustre localhost --no-dbspace-check
