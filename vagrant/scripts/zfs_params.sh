#!/bin/bash

mkdir -p /sys/module/zfs/parameters
echo 100 > /sys/module/zfs/parameters/zfs_multihost_history
echo 60 > /sys/module/zfs/parameters/zfs_multihost_fail_intervals
echo options zfs zfs_multihost_history=100 > /etc/modprobe.d/iml_zfs_module_parameters.conf
echo options zfs zfs_multihost_fail_intervals=60 >> /etc/modprobe.d/iml_zfs_module_parameters.conf
