#!/bin/bash

yum install -y yum-plugin-copr
yum copr enable -y managerforlustre/manager-for-lustre-devel
mkdir -p /tmp/agent-rpms
scp adm:/tmp/agent-rpms/*.rpm /tmp/agent-rpms
yum localinstall -y /tmp/agent-rpms/*.rpm