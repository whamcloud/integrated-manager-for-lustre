#!/bin/bash

TIMEOUT=300

NAME=${1:-emf}

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

crm res stop ${NAME}-docker-grp
waitstop ${NAME}-docker-grp

crm config delete ${NAME}-docker docker ${NAME}-fs ${NAME}-ip
clush -a sed -i '/nginx$/d' /etc/hosts
