#!/bin/bash

exec 2>&1

set -e
set -x

mmp_status() {
    local verbose="$1"
    local only_this_host="$2"
    local disk="$3"

    read -r interval mmp_time host < <(debugfs -c -R dump_mmp "$disk" 2>/dev/null |
                                    sed -ne '/^update_interval: /s///p' \
                                         -e '/^node_name: /s///p' \
                                         -e '/^time:/s/.*: \([0-9][0-9]*\).*/\1/p' |
                                    tr '\n' ' ') || true
    if [ -z "$interval" ] || [ -z "$mmp_time" ] || [ -z "$host" ]; then
        if $verbose; then
            echo "Could not read MMP block from $disk"
        fi
        # no MMP block so it's not an in-use ldiskfs device
        return 0
    fi

    now=$(date +%s)
    diff=$((now - mmp_time))
    #echo $diff $mmp_time $now $host $interval
    if [ "$diff" -gt "$interval" ]; then
        active=false
    else
        active=true
    fi
    if $active; then
        if [ "$host" = "$HOSTNAME" ]; then
            host="this host"
            rc=1
            if $verbose; then
                date
                debugfs -c -R dump_mmp "$disk"
                get_lustre_mounts true
            fi
        else
            if $only_this_host; then
                rc=0
            else
                rc=2
            fi
        fi
        if $verbose; then
            echo "$disk in use on $host, last updated $diff seconds ago"
        fi
    else
        if $verbose; then
            echo "not in use"
        fi
        rc=0
    fi

    return $rc

}

get_proc_mounts() {
    local exclude="${1:-###########}"

    egrep -v "$exclude" /proc/mounts || true

}

get_lustre_mounts() {
    header="${1:false}"

    if $header; then
        echo "---------- /proc/mounts ----------"
    fi
    get_proc_mounts " ((config|rpc_pipe|security|debug|hugetlb|root|sys|auto|tmp)fs|pstore|mqueue|nfs[d4]|ext[234]|proc|dev(tmpfs|pts)|cgroup) "

}

echo "$HOSTNAME"

date

pcs status || true

get_lustre_mounts true

systemctl stop pcsd pacemaker corosync
systemctl disable pcsd pacemaker corosync

date

get_lustre_mounts true

for d in a b c d e; do
    mmp_status true false /dev/sd$d || true
done
sleep 60
if grep " lustre " /proc/mounts; then
    umount -t lustre -a
    get_lustre_mounts
    sleep 60
fi
get_lustre_mounts true
# if any devices report !0 now, they are still active and they should not be!
for d in a b c d e; do
    if ! mmp_status true true /dev/sd$d; then
        mmp_status_rc=${PIPESTATUS[0]}
        pgrep -l kmmpd
        dmesg
        lctl dk > /var/tmp/lustre_debug_umount-"$(date +%s)".log
        cat <<EOF | mail -s "umount failure" brian.murrell@intel.com
got a node with a umount problem on $HOSTNAME

$(rpm -qa | grep chroma)
EOF
        cat <<EOF > /tmp/waiting_help
mmp_status returned $mmp_status_rc for /dev/sd$d.  Wating for help on LU-9925.

When done, you can put continue status into /tmp/waiting_help_rc.  Use 0 to
continue as if nothing went wrong, or any other value to exit the script
with that value.

If you want to just let the script continue with the mmp_status() return code
don't create the /tmp/waiting_help_rc file."
EOF
        while [ -e /tmp/waiting_help ]; do
            sleep 1
        done
        continue_rc="$mmp_status_rc"
        if [ -f /tmp/waiting_help_rc ]; then
            read -r continue_rc < /tmp/waiting_help_rc
            rm -f /tmp/waiting_help_rc
        fi
        if [ "$continue_rc" -ne 0 ]; then
            exit "$continue_rc"
        fi
    fi
done

# figure it out for ourselves if we can
# otherwise the caller needs to have set it
if [ -f /etc/corosync/corosync.conf ]; then
    ring1_iface=$(ip route get "$(sed -ne '/ringnumber: 1/{s///;n;s/.*: //p}' /etc/corosync/corosync.conf)" | sed -ne 's/.* dev \(.*\)  *src.*/\1/p')
fi

ifconfig "$ring1_iface" 0.0.0.0 down

rm -f /etc/sysconfig/network-scripts/ifcfg-"$ring1_iface"
rm -f /etc/corosync/corosync.conf
rm -f /var/lib/pacemaker/cib/*
rm -f /var/lib/corosync/*

exit 0
