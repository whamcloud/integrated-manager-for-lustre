#!/bin/bash

set -xe

if pcs status ; then
    pcs cluster stop --all
fi

# figure it out for ourselves if we can
# otherwise the caller needs to have set it
if [ -f /etc/corosync/corosync.conf ]; then
    ring0_iface=$(ip route get "$(sed -ne '/ringnumber: 0/{s///;n;s/.*: //p}' /etc/corosync/corosync.conf)" | sed -ne 's/.* dev \([^ ]*\)  *src.*/\1/p')
fi

pcs cluster destroy
systemctl disable --now pcsd pacemaker corosync

if [ -n "$ring0_iface" ]; then
    ifdown "$ring0_iface"
    rm -f /etc/sysconfig/network-scripts/ifcfg-"$ring0_iface"
fi

rm -f /etc/corosync/corosync.conf
rm -f /var/lib/pacemaker/cib/*
rm -f /var/lib/corosync/*

exit 0
