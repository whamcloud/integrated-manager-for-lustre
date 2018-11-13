#!/bin/bash

set -e
pcs cluster stop --all


# figure it out for ourselves if we can
# otherwise the caller needs to have set it
if [ -f /etc/corosync/corosync.conf ]; then
    ring1_iface=$(ip route get "$(sed -ne '/ringnumber: 1/{s///;n;s/.*: //p}' /etc/corosync/corosync.conf)" | sed -ne 's/.* dev \([^ ]*\)  *src.*/\1/p')
fi

ifconfig "$ring1_iface" 0.0.0.0 down

pcs cluster destroy
systemctl disable --now pcsd pacemaker corosync

rm -f /etc/sysconfig/network-scripts/ifcfg-"$ring1_iface"
rm -f /etc/corosync/corosync.conf
rm -f /var/lib/pacemaker/cib/*
rm -f /var/lib/corosync/*

exit 0
