#!/bin/bash

NTP_SERVER=$1

systemctl disable --now chronyd
yum install -y ntp sntp
# delete all server entries
sed -i -e "/^server /d" /etc/ntp.conf
# Append ntp server address 
sed -i -e "$ a server $NTP_SERVER iburst" /etc/ntp.conf

sntp "$NTP_SERVER"
sntp "$NTP_SERVER"

systemctl enable --now ntpd.service
