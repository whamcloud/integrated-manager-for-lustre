#!/bin/bash -ex

nodes="$1"

# wait for rebooted nodes
sleep 5
RUNNING_TIME=0
while [ -n "$nodes" ] && [ $RUNNING_TIME -lt 500 ]; do
    for node in $nodes; do
        if ssh root@$node uptime; then
            nodes=$(echo "$nodes" | sed -e "s/$node//" -e 's/^ *//' -e 's/ *$//')
        fi
    done
    (( RUNNING_TIME++ )) || true
    sleep 1
done

if [ -n "$nodes" ]; then
    echo "Nodes: $nodes failed to come back after a reboot"
    exit 1
fi
