#!/bin/bash

NTP_SERVER=$1

until ntpstat;
do
  ntpdate -qu "$NTP_SERVER"
  sleep 30
done