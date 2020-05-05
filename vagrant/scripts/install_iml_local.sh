#!/bin/bash

set -ex

yum copr enable -y managerforlustre/manager-for-lustre-devel
yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
yum install -y git ed epel-release python-setuptools gcc openssl-devel postgresql96-devel
curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env
rustup update
rustc --version
cargo --version
cd /integrated-manager-for-lustre

make local

rm -rf /tmp/{manager,agent}-rpms
mkdir -p /tmp/{manager,agent}-rpms

cp /integrated-manager-for-lustre/_topdir/RPMS/x86_64/rust-iml-{action-runner,agent-comms,api,cli,mailbox,ntp,ostpool,postoffice,stats,device,warp-drive}-*.rpm /tmp/manager-rpms/
cp /integrated-manager-for-lustre/_topdir/RPMS/noarch/python2-iml-manager-*.rpm /tmp/manager-rpms/
cp /integrated-manager-for-lustre/_topdir/RPMS/x86_64/rust-iml-agent-[0-9]*.rpm /tmp/agent-rpms
cp /integrated-manager-for-lustre/chroma_support.repo /etc/yum.repos.d/

yum install -y /tmp/manager-rpms/*.rpm

chroma-config setup admin lustre localhost --no-dbspace-check
