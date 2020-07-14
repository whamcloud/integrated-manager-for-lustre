#!/bin/bash

NTP_SERVER=$1

systemctl stop ntpd.service

sntp -s "$NTP_SERVER"
sntp -s "$NTP_SERVER"

systemctl restart ntpd.service

until ntpstat;
do
  sleep 10
done