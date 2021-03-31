#!/bin/bash

if command -v yum  &>/dev/null ; then
    yum autoremove emf-docker rust-emf-agent -y
elif command -v apt-get &>/dev/null ; then
    apt-get remove emf-agent -y
fi
