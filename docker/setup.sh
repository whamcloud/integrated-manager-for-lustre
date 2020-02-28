#!/bin/sh
set -e

echo "Starting db check"

until psql -h 'postgres' -U 'chroma' -c '\q'; do
  echo "Waiting for postgres"
  sleep 5
done

echo "Starting setup"
PW=$(cat /run/secrets/iml_pw)
chroma-config container-setup admin $PW

echo "Registering Repos/Profiles"
SETUPDIR=/var/lib/chroma-setup
DATADIR=/var/lib/chroma

for repo in $(ls $SETUPDIR/ |grep .repo$); do
    mkdir -p $DATADIR/repo
    cp $repo $DATADIR/repo/
    chroma-config repos register $DATADIR/repo/$(basename $repo)
done

for profile in $(ls $SETUPDIR/ |grep .profile$); do
    chroma-config profile register $profile
done
