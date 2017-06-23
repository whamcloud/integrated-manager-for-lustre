# Install the IEEL Lustre client
ssh root@$CLIENT_1 "exec 2>&1; set -xe

mkdir lustre_client_rpms
cd lustre_client_rpms

# Add the client repo
cat << EOF > /etc/yum.repos.d/lustre-client.repo
[lustre-client]
name=lustre-client
baseurl=https://build.whamcloud.com/job/lustre-master/lastSuccessfulBuild/arch=x86_64%2Cbuild_type=client%2Cdistro=el7%2Cib_stack=inkernel/artifact/artifacts/
enabled=1
sslverify=0
gpgcheck=0

[temp-updates]
name=temp-updates
baseurl=http://mirror.centos.org/centos/7/updates/x86_64/
enabled=1
sslverify=0
gpgcheck=0
EOF

# disable the server repo
yum-config-manager --disable lustre

yum -y install --disablerepo=* --enablerepo=temp-updates kernel-3.10.0-514.21.1.el7

yum -y install lustre-client

sleep 9999
reboot"

