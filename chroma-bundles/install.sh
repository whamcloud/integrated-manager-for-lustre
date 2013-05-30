#!/bin/bash

trap "set +x; echo \"There was an error installing, please see /tmp/install.log\"" ERR
set -e

exec 2>/tmp/install.log
set -x


TMPDIR=${TMPDIR:-/var/tmp}

# unpack and place bundles
BUNDLE_ROOT=/var/lib/chroma/repo

echo "Installing bundles"
for bundle in *-bundle.tar.gz; do
    bndl=${bundle%%-bundle.tar.gz}
    register_bundles="$register_bundles $bndl"
    mkdir -p "$BUNDLE_ROOT/$bndl"
    tar -C "$BUNDLE_ROOT/$bndl" -xzf "$bundle"
done

# now, make the temporary chroma-manager repo
REPOTMPD=$(mktemp -d)
REPOTMP=$(mktemp /etc/yum.repos.d/XXXXXX.repo)
trap "rm -rf \"$REPOTMPD\" \"$REPOTMP\"" EXIT
tar -C "$REPOTMPD" -xzf chroma-manager.tar.gz
cat <<EOF >"$REPOTMP"
[chroma-manager]
name=chroma-manager
baseurl=file://$REPOTMPD
gpgcheck=0
enable=0
EOF

# and install from it
echo "Installing Intel Manager for Lustre Control Center"
yum -y --enablerepo=chroma-manager install chroma-manager >&2

chroma-config setup 2>&1

echo "Registering bundles"
for bundle in $register_bundles; do
    chroma-config bundle register "$BUNDLE_ROOT/$bundle"
done

echo "Registering profiles"
for profile in *.profile; do
    chroma-config profile register $profile
done
