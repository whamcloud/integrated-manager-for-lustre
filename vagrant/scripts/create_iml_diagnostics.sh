#! /bin/bash

PREFIX=$1

# Clean out any existing sos reports on this node
yum install -y sos
rm -f /var/tmp/*sosreport*
sosreport --batch -k docker.all=on -k docker.logs=on
cd /var/tmp || exit 1
for f in *sosreport*.tar.xz; do mv "$f" "$PREFIX"_"$f"; done