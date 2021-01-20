#!/bin/bash

# default timeout 10 minutes
TIMEOUT=600

waitstart () {
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
            if [ -z "$res" ]; then
                NOTDONE=true
                [ $((timeout % 10)) == 0 ] && echo -n "."
                sleep 2
                break
            fi
        done

        let timeout-=2
    done

    echo ""

    if ((timeout == 0)); then
        echo "Waiting for $IDS TIMED OUT!"
        exit 1
    fi
}

function locate_resource() {
    res=$1
    crm_resource -QW -r $res 2> /dev/null
}

clush -a "es_install --steps esui --yes"

config-pacemaker --type esui

waitstart esui-docker

# this probably will run on node1 (but not guaranteed)
ssh $(locate_resource "esui-docker-grp") "es_install --steps esui_scan --yes"
