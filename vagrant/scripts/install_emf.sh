#!/bin/bash

yum-config-manager --add-repo=$1
yum install -y python2-emf-manager
chroma-config setup admin lustre localhost --no-dbspace-check -v
