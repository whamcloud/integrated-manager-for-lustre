#!/bin/bash

until ntpstat;
do
  sleep 10
done