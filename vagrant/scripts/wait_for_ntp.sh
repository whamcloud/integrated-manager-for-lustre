#!/bin/bash

NTP_SERVER=$1

ntpdate -qu "$NTP_SERVER"

systemctl restart ntpd.service

until ntpstat;
do
  sleep 70
done