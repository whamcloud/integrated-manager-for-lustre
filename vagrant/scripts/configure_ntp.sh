#!/bin/bash

NTP_SERVER=$1

sudo systemctl disable --now chronyd
sudo yum install -y ntp
# delete all server entries
sudo sed -i -e "/^server /d" /etc/ntp.conf
# Append ntp server address 
sudo sed -i -e "$ a server $NTP_SERVER iburst" /etc/ntp.conf
sudo systemctl restart ntpd.service
sudo systemctl enable ntpd.service

sleep 30

until ntpstat;
do
  ntpdate -qu "$NTP_SERVER"
  sleep 30
done