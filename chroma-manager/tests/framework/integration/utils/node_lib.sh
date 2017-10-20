#!/bin/bash

# Functions to deal with nodes

# shellcheck disable=SC2034
REBOOT_NODE="sync
sync
nohup bash -c \"sleep 2; init 6\" >/dev/null 2>/dev/null </dev/null & exit 0"

reset_node() {
    local node="$1"

    local domstate
    domstate="$(virsh domstate "$node" 2>&1)"
    if [[ $domstate = error:\ failed\ to\ get\ domain* ]]; then
        echo "can't reset an undefined domain for node $node in reset_node()"
        return 1
    fi
    if [ "$domstate" = "shut off" ]; then
        # already destroyed
        virsh start "$node"
        return 0
    fi
    if [ "$domstate" = "paused" ]; then
        virsh resume "$node"
        domstate="$(virsh domstate "$node" 2>&1)"
        if [ "$domstate" = "paused" ]; then
            echo "unable to resume domain $node from paused state"
            return 1
        fi
    fi
    if [ "$domstate" = "running" ]; then
        virsh reset "$node"
        return 0
    fi

    echo "unknown domain state for node $node in reset_node(): $domstate"
    return 1
}

restart_node() {
    local node="$1"

    virsh destroy "$node"
    virsh start "$node"

}

restart_nodes() {
    local nodes="$*"

    for node in $nodes; do
        restart_node "$node"
    done
}

reset_nodes() {
    local nodes="$*"

    for node in $nodes; do
        reset_node "$node"
    done

}

remove_nodes_from_list() {
    local nodes_array=($1)
    local remove_nodes="$2"

    for node in $remove_nodes; do
        nodes_array=(${nodes_array[@]/$node})
    done

    echo "${nodes_array[@]}"
}

unavailable_nodes () {
    local nodes="$*"

    local node
    for node in $nodes; do
        if ssh root@"$node" id >&2; then
            nodes=$(remove_nodes_from_list "$nodes" "$node")
        fi
    done

    echo "$nodes"
}

wait_for_nodes() {
    local nodes="$*"

    # 90 seconds seems to be long enough for VMs to start
    TIMEOUT=${TIMEOUT:-90}
    local start=$SECONDS
    local iters=1
    local max_iters=${MAX_TIMES:-1}

    # wait for any rebooted nodes
    while [ -n "$nodes" ] && [ "$iters" -le "$max_iters" ]; do
        nodes=$(unavailable_nodes "$nodes")
        # and reset them if they fail to come up
        # they don't actually fail to come up.  for some reason the DHCP
        # server fails to create DNS records sometimes so resetting them
        # gives the DHCP server another chance to try
        if [ $((SECONDS-start)) -gt "$TIMEOUT" ]; then
            if ${BOOT_FAIL_NOTIFY:-false}; then
                mail -s "failed nodes boot on $HOSTNAME" brian.murrell@intel.com <<EOF
Nodes for cluster ${CLUSTER_NUM:-0} failed to come up the first time
on $HOSTNAME after waiting $TIMEOUT for them."
EOF
            fi
            if [ $iters -lt 2 ]; then
                reset_nodes "$nodes"
            else
                # actually sometimes they fail to come up after a reset but
                # succeed after a complete restart
                restart_nodes "$nodes"
            fi
            let iters=$iters+1
            if [ -z "$MAX_TIMES" ]; then
                # caller didn't set a limit so increase $max_iters
                let max_iters=$max_iters+1
            fi
            # reset the timer
            start=$SECONDS
        fi
        sleep 1
    done

    # if there are still some unavailable, let's see what we can
    # learn about them
    (local node
    for node in $nodes; do
        cat <<EOF
--------------------
$node
--------------------
EOF
        ping -c 1 "$node"
        # grab the last 50 lines of console
        tail -50 /scratch/logs/console/"${node}".log
    done) >&2

}
