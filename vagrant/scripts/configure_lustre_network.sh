#!/bin/bash

modprobe lnet
lnetctl lnet configure
lnetctl net add --net tcp0 --if eth1
lnetctl net show --net tcp > /etc/lnet.conf
systemctl enable lnet.service
