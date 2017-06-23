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
EOF

# disable the server repo
yum-config-manager --disable lustre

# install kernel kmod-lustre-client was built for
# TODO: derive this rather than hard-coding
yum -y install kernel-3.10.0-514.21.1.el7

# Installed a kernel, so need a reboot
sync
sync
nohup bash -c \"sleep 2; init 6\" >/dev/null 2>/dev/null </dev/null & exit 0"

ssh root@$CLIENT_1 "exec 2>&1; set -xe
yum -y install lustre-client

modinfo lustre
modprobe lustre"
