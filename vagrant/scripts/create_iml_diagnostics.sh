#! /bin/bash

HOST_IP=$1
PREFIX=$2

# Clean out any existing sos reports on this node
rm -f /var/tmp/*sosreport*
iml-diagnostics
for f in sosreport*.tar.xz; do mv "$f" "$PREFIX"_"$f"; done
scp /var/tmp/sosreport* "$HOST_IP":/tmp