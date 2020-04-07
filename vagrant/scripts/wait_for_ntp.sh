#!/bin/bash

NTP_SERVER=$1

ntpdate -qu "$NTP_SERVER"

until ntpstat;
do
  sleep 70
done