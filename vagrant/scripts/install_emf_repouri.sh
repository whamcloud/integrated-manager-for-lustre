#!/bin/bash

set -ex

if [[ -z $REPO_URI ]];
then
    echo "REPO_URI must be set to use this provisioner"
    exit 1
fi

cat <<EOF > /etc/yum.repos.d/manager-for-lustre.repo
[manager-for-lustre]
name=manager-for-lustre
baseurl=$REPO_URI
enabled=1
gpgcheck=0

[managerforlustre-manager-for-lustre-devel]
name=Copr repo for manager-for-lustre-devel owned by managerforlustre
baseurl=https://copr-be.cloud.fedoraproject.org/results/managerforlustre/manager-for-lustre-devel/epel-7-\$basearch/
type=rpm-md
skip_if_unavailable=True
gpgcheck=1
gpgkey=https://copr-be.cloud.fedoraproject.org/results/managerforlustre/manager-for-lustre-devel/pubkey.gpg
repo_gpgcheck=0
enabled=1

[influxdb]
name = InfluxDB Repository - RHEL 7
baseurl = https://repos.influxdata.com/centos/7/\$basearch/stable
enabled = 1
gpgcheck = 1
gpgkey = https://repos.influxdata.com/influxdb.key

[grafana]
name=grafana
baseurl=https://packages.grafana.com/oss/rpm
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://packages.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt

[pgdg96]
name=PostgreSQL 9.6 for RHEL/CentOS \$releasever - \$basearch
baseurl=https://download.postgresql.org/pub/repos/yum/9.6/redhat/rhel-\$releasever-\$basearch
enabled=1
gpgcheck=1
gpgkey=https://download.postgresql.org/pub/repos/yum/RPM-GPG-KEY-PGDG-96
EOF

yum install -y python2-emf-manager

cat <<EOF > /usr/share/chroma-manager/base.repo
[manager-for-lustre]
name=manager-for-lustre
baseurl=$REPO_URI
enabled=1
gpgcheck=0

[managerforlustre-manager-for-lustre-devel]
name=Copr repo for manager-for-lustre-devel owned by managerforlustre
baseurl=https://copr-be.cloud.fedoraproject.org/results/managerforlustre/manager-for-lustre-devel/epel-7-\$basearch/
type=rpm-md
skip_if_unavailable=True
gpgcheck=1
gpgkey=https://copr-be.cloud.fedoraproject.org/results/managerforlustre/manager-for-lustre-devel/pubkey.gpg
repo_gpgcheck=0
enabled=1
EOF

chroma-config setup admin lustre localhost --no-dbspace-check -v