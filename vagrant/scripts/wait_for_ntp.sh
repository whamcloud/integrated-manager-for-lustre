#!/bin/bash

NTP_SERVER=$1

sntp -s "$NTP_SERVER"

systemctl restart ntpd.service

until ntpstat;
do
  sleep 10
done