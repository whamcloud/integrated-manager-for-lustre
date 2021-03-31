#!/bin/bash
# This should only run on node1

if ! [ -d emf-repo-rpm ] ; then echo "emf-repo-rpm directory is missing in $PWD" ; exit 1 ; fi

yum install emf-repo-rpm/* -y 

if ! echo "[emf]
name=emf repo
baseurl=file:///var/lib/emf/repo/emf_repo/
gpgcheck=0" > /etc/yum.repos.d/emf.repo ; then echo "Can't update /etc/yum.repos.d/emf.repo" ; exit 1 ; fi
