#!/bin/bash

FS=${1:-fs}

mkdir /mnt/$FS
mount -t lustre 10.73.20.11@tcp:10.73.20.12@tcp:/$FS /mnt/$FS

