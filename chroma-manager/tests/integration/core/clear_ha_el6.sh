#!/bin/sh

set -ex

service pacemaker stop
service corosync stop

ifconfig eth1 0.0.0.0 down

rm -f /etc/sysconfig/network-scripts/ifcfg-eth1
rm -f /etc/corosync/corosync.conf
rm -f /var/lib/pacemaker/cib/*
rm -f /var/lib/corosync/*
