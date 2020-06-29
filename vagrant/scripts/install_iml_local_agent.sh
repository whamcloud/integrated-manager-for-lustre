#!/bin/bash

yum install -y yum-plugin-copr
yum copr enable -y managerforlustre/manager-for-lustre-devel
rm -rf /tmp/agent-rpms
mkdir -p /tmp/agent-rpms
scp adm:/tmp/agent-rpms/*.rpm /tmp/agent-rpms
yum install -y /tmp/agent-rpms/*.rpm