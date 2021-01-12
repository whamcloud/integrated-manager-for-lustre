#!/bin/bash

mkdir -p /tmp/emf-install
cd /tmp/emf-install
curl -L https://github.com/whamcloud/exascaler-management-framework/releases/download/v$1/emf-$1.tar.gz | tar zx --strip 1
yum install -y expect
curl -O https://raw.githubusercontent.com/whamcloud/integrated-manager-for-lustre/v$1/chroma-manager/tests/utils/install.exp
/usr/bin/expect install.exp admin "" lustre ""