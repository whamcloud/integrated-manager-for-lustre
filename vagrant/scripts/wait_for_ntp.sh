#!/bin/bash

until ntpstat;
do
  systemctl restart ntpd.service
  sleep 30
done