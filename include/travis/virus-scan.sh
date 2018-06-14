#!/bin/bash -xe

sudo apt-get install clamav -y
sudo freshclam
clamscan --quiet -r ./
