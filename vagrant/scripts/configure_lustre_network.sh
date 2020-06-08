#!/bin/bash

DEV=$(ip r get 10.73.20.1|awk '/dev/{ print $3 }')

modprobe lnet
lnetctl lnet configure
lnetctl net add --net tcp0 --if $DEV
lnetctl net show --net tcp > /etc/lnet.conf
systemctl enable lnet.service
