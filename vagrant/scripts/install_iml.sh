#!/bin/bash

yum-config-manager --add-repo=$1
yum install -y python2-iml-manager
chroma-config setup admin lustre localhost --no-dbspace-check -v
