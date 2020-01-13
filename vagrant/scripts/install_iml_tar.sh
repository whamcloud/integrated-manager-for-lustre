#!/bin/bash

mkdir -p /tmp/iml-install
cd /tmp/iml-install
curl -L https://github.com/whamcloud/integrated-manager-for-lustre/releases/download/v$1/iml-$1.tar.gz | tar zx --strip 1
yum install -y expect
curl -O https://raw.githubusercontent.com/whamcloud/integrated-manager-for-lustre/v$1/chroma-manager/tests/utils/install.exp
/usr/bin/expect install.exp admin "" lustre ""