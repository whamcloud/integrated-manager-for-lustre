#!/bin/bash

TIMEOUT=300

waitstop () {
    IDS=$*

    [ -z "$IDS" ] && return

    echo -n "Waiting for $IDS"

    local timeout=$TIMEOUT

    local NOTDONE=true
    while $NOTDONE && ((timeout > 0)); do

        NOTDONE=false
        for i in $IDS; do
            # This finds the host the resource is active on (empty it is stopped)
            res=$(crm_resource -QW -r $i 2> /dev/null)
            if [ -n "$res" ]; then
                NOTDONE=true
                [ $((timeout % 10)) == 0 ] && echo -n "."
                sleep 1
                break
            fi
        done

        let timeout-=1
    done

    echo ""

    if ((timeout == 0)); then
        echo "Waiting for $IDS TIMED OUT!"
        exit 1
    fi
}

clush -a systemctl disable --now emf-storage-server.target iml-storage-server.target

crm res stop esui-docker-grp
waitstop esui-docker-grp

crm config delete esui-docker docker esui-fs esui-ip
clush -a sed -i '/nginx$/d' /etc/hosts
