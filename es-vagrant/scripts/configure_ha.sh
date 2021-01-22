#!/bin/bash

[ -f /etc/corosync/authkey ] || config-corosync --gen-authkey
sync-file /etc/corosync/authkey
clush -a systemctl start corosync pacemaker
for i in {1..120}; do
    if cibadmin --query > /dev/null; then
        break
    fi
    sleep 1
done
config-pacemaker
