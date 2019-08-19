#!/bin/bash

debug() {
    logger -t clear_ha "$@"
    echo "clear_ha: $@"
}

set -e

debug "Stopping cluster"
if pcs status ; then
    pcs cluster stop --all
fi

# figure it out for ourselves if we can if caller didn't set it
if [ -z "$ring0_iface" ] && [ -f /etc/corosync/corosync.conf ]; then
    ring0_iface=$(ip route get "$(sed -ne '/ringnumber: 0/{s///;n;s/.*: //p}' /etc/corosync/corosync.conf)" | sed -ne 's/.* dev \([^ ]*\)  *src.*/\1/p')
fi

debug "Destroying cluster"
pcs cluster destroy
debug "Stopping cluster services"
systemctl disable --now pcsd pacemaker corosync

debug "Stopping interface $ring0_iface"
if [ -n "$ring0_iface" ] && ip link show "$ring0_iface"; then
    ifconfig "$ring0_iface" 0.0.0.0 down
    rm -f /etc/sysconfig/network-scripts/ifcfg-"$ring0_iface"
fi

rm -f /etc/corosync/corosync.conf
rm -f /var/lib/pacemaker/cib/*
rm -f /var/lib/corosync/*

debug "Finished"
exit 0
