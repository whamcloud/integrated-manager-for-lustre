#! /bin/bash

PREFIX=$1

# Clean out any existing sos reports on this node
rm -f /var/tmp/*sosreport*
iml-diagnostics
cd /var/tmp || exit 1
for f in *sosreport*.tar.xz; do mv "$f" "$PREFIX"_"$f"; done