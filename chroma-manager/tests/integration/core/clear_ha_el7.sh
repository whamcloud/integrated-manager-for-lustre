#!/bin/bash

set -e
set -x

mmp_status() {
    local verbose="$1"
    local disk="$2"

    read interval mmp_time host < <(debugfs -c -R dump_mmp $disk 2>/dev/null |
                                    sed -ne '/^update_interval: /s///p' \
                                         -e '/^node_name: /s///p' \
                                         -e '/^time:/s/.*: \([0-9][0-9]*\).*/\1/p' |
                                    tr '\n' ' ')
    if [ -z "$interval" -o -z "$mmp_time" -o -z "$host" ]; then
        if $verbose; then
            echo "Could not read MMP block from $1"
        fi
        return 4
    fi

    now=$(date +%s)
    diff=$((now - mmp_time))
    #echo $diff $mmp_time $now $host $interval
    if [ $diff -gt $interval ]; then
        if $verbose; then
            echo "not in use"
        fi
        rc=0
    else
        if [ $host = $HOSTNAME ]; then
            host="this host"
            rc=1
        else
            rc=2
        fi
        if $verbose; then
            echo "$disk in use on $host, last updated $diff seconds ago"
        fi
    fi
    return $rc
}

date
pcs status

systemctl stop pcsd pacemaker corosync
systemctl disable pcsd pacemaker corosync

date

cat /proc/mounts

for d in a b c d e; do
    mmp_status -v /dev/sd$d || true
done
sleep 60
if grep " lustre " /proc/mounts; then
    umount -t lustre -a
    cat /proc/mounts
    sleep 60
fi
cat /proc/mounts
# if any devices report !0 now, they are still active and they should not be!
for d in a b c d e; do
    mmp_status -v /dev/sd$d
done

# figure it out for ourselves if we can
# otherwise the caller needs to have set it
if [ -f /etc/corosync/corosync.conf ]; then
    ring1_iface=$(ip route get $(sed -ne '/ringnumber: 1/{s///;n;s/.*: //p}' /etc/corosync/corosync.conf) | sed -ne 's/.* dev \(.*\)  *src.*/\1/p')
fi

ifconfig $ring1_iface 0.0.0.0 down

rm -f /etc/sysconfig/network-scripts/ifcfg-$ring1_iface
rm -f /etc/corosync/corosync.conf
rm -f /var/lib/pacemaker/cib/*
rm -f /var/lib/corosync/*

exit 0
