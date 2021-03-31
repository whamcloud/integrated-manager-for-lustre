#!/bin/bash

id_rsa_dir=es-vagrant/
if ! [ -f ${id_rsa_dir}id_rsa ] ; then
    if ! [ -f id_rsa ] ; then
	echo "id_rsa not found in $PWD/${id_rsa_dir}/id_rsa || $PWD/id_rsa"
	exit 1
    fi
    id_rsa_dir=""
fi

ID_FILE_PATH="$PWD/${id_rsa_dir}id_rsa"
for i in 1 2 3 4 ; do
    if ! grep -q -E "^Host[[:space:]]+node$i(\$|[[:space:]]+)" ~/.ssh/config ; then
	cat <<EOF >> ~/.ssh/config

Host node$i
  HostName 10.73.10.1$i
  User root
  UserKnownHostsFile /dev/null
  StrictHostKeyChecking no
  PasswordAuthentication no
  IdentityFile $ID_FILE_PATH
  IdentitiesOnly yes
  LogLevel FATAL
EOF
    else
	echo "⚠  node$i already present in ~/.ssh/config"
    fi
done

# Check there is a route
if ! ip a |grep -q -E "inet 10.73.[0-9]+.[0-9]+/24" ; then
    echo "⚠  No route found to reach VM IPs"
    echo "If 'ssh node1' doesn't work you can try with:"
    echo "vboxmanage hostonlyif ipconfig vboxnet0 --ip 10.73.10.2 --netmask 255.255.255.0"
    exit 1
fi

