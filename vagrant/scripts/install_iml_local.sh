#!/bin/bash

yum copr enable -y managerforlustre/manager-for-lustre-devel
yum install -y rpmdevtools git ed epel-release python-setuptools
cd /integrated-manager-for-lustre
make rpms
cp ./chroma_support.repo /etc/yum.repos.d/
yum install -y /integrated-manager-for-lustre/_topdir/RPMS/noarch/python2-iml-manager-*
chroma-config setup admin lustre localhost --no-dbspace-check
