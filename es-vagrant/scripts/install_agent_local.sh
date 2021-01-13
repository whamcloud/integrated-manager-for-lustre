#!/bin/bash

yum install -y yum-plugin-copr
yum copr enable -y managerforlustre/manager-for-lustre-devel
yum install -y /vagrant/agent-rpms/*.rpm
