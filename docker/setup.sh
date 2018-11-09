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