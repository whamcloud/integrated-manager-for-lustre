#!/bin/bash

systemctl disable --now chronyd
yum install -y ntp
# delete all server entries
sed -i -e "/^server /d" /etc/ntp.conf
# Append ntp server address
sed -i -e "$ a server 127.127.1.0" /etc/ntp.conf
sed -i -e "$ a fudge 127.127.1.0 stratum 10" /etc/ntp.conf

systemctl enable --now ntpd.service
