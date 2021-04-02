#!/bin/bash
# This should only run on node1

if ! yum install rust-emf-manager -y ; then echo "Can't install rust-emf-manager" ; exit 1 ; fi

if ! EMF_PG_SKIP_CHECK=1 emf-config bootstrap ; then echo "Can't use emf-config boostrap" ; exit 1 ; fi


if ! systemctl enable \
emf-manager.target \
emf-api \
emf-device \
emf-host \
emf-journal \
emf-network \
emf-ntp \
emf-ostpool \
emf-rust-stats \
emf-rust-corosync \
emf-state-machine \
	  emf-warp-drive ; then echo "Can't enable emf services" ; exit 1 ; fi

if ! systemctl start emf-manager.target ; then
    echo "Can't start emf-manager.target service"
    exit 1
fi

if ! echo 'SERVER_HTTP_URL=https://node1:7443' > /etc/emf/cli.conf ; then
    echo "Can't write SERVER_HTTP_URL to /etc/emf/cli.conf"
    exit 1
fi

if  ! emf host deploy node[1-4] --flavor server ; then
    echo "Can't deploy emf to servers"
    exit 1
fi

if ! emf host deploy ubuntu1 --flavor ubuntu ; then
    echo "Can't deploy emf to clients"
    exit 1
fi

echo "Waiting for emf host list"
until emf host list > /dev/null 2>&1; do sleep 1; done
