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

[lustre-server]
name=lustre-server
baseurl=https://build.whamcloud.com/job/lustre-master/lastSuccessfulBuild/arch=x86_64%2Cbuild_type=server%2Cdistro=el7%2Cib_stack=inkernel/artifact/artifacts/
enabled=1
sslverify=0
gpgcheck=0
EOF

# disable the server repo
# yum-config-manager --disable lustre
yum -y install --disablerepo=* --enablerepo=lustre-server kernel kernel-devel kernel-headers

yum -y install lustre-client

modprobe lustre"
