#!/bin/bash

set -ex

yum copr enable -y managerforlustre/manager-for-lustre-devel
# Get latest rpmdevtools
yum install -y https://copr-be.cloud.fedoraproject.org/results/managerforlustre/buildtools/epel-8-x86_64/01152137-rpmdevtools/rpmdevtools-8.10-7.el8.noarch.rpm
yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
yum install -y rpmdevtools git ed epel-release python-setuptools gcc openssl-devel postgresql12-devel
curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env
rustup update
rustc --version
cargo --version
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

make all

yum autoremove -y rpmdevtools

rm -rf /tmp/{manager,agent}-rpms
mkdir -p /tmp/{manager,agent}-rpms

cp /integrated-manager-for-lustre/_topdir/RPMS/x86_64/rust-iml-{action-runner,agent-comms,api,cli,mailbox,ostpool,postoffice,stats,device,warp-drive}-*.rpm /tmp/manager-rpms/
cp /integrated-manager-for-lustre/_topdir/RPMS/noarch/python2-iml-manager-*.rpm /tmp/manager-rpms/
cp /integrated-manager-for-lustre/_topdir/RPMS/x86_64/rust-iml-agent-[0-9]*.rpm /tmp/agent-rpms
cp /integrated-manager-for-lustre/chroma_support.repo /etc/yum.repos.d/

yum install -y /tmp/manager-rpms/*.rpm
echo 'pathmunge /usr/pgsql-12/bin' > /etc/profile.d/postgres.sh
chmod +x /etc/profile.d/postgres.sh
. /etc/profile

chroma-config setup admin lustre localhost --no-dbspace-check
