#!/bin/sh

set -ex

systemctl stop corosync pacemaker pcsd
systemctl disable corosync pacemaker pcsd

ifconfig eth1 0.0.0.0 down

rm -f /etc/sysconfig/network-scripts/ifcfg-eth1
rm -f /etc/corosync/corosync.conf
rm -f /var/lib/pacemaker/cib/*
rm -f /var/lib/corosync/*
