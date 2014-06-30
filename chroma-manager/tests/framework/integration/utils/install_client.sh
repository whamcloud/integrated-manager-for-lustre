#!/bin/bash -ex

[ -r localenv ] && . localenv

# Install the IEEL Lustre client
ssh root@$CLIENT_1 <<EOC
exec 2>&1; set -xe

mkdir lustre_client_rpms
cd lustre_client_rpms

# Add the client repo created on the manager at installation
yum-config-manager --add-repo=https://$CHROMA_MANAGER/client
cat << "EOF" >> /etc/yum.repos.d/${CHROMA_MANAGER}_client.repo
sslverify=0
gpgcheck=0
EOF

$PROXY yumdownloader lustre-client lustre-client-modules

# Extract what kernel version and release we need to match the client rpms
# rpm -qpr will list the dependencies of the rpm, and the sed strips out the
# other dependencies and the 'kernel = ' at the beggining of the line.
KERNEL_VERSION_AND_RELEASE="\$(rpm -qpR lustre-client-modules-* | sed -n -e '/^kernel =/s/.* = //p')";

$PROXY yumdownloader kernel-\$KERNEL_VERSION_AND_RELEASE kernel-firmware-\$KERNEL_VERSION_AND_RELEASE  # Have to install explicitly to avoid getting kernel-debug in the automatic dependency resolution

if ! rpm -q \$(rpm -qp kernel-firmware-*.rpm); then
    rpm -Uvh --oldpackage kernel-firmware-*.rpm
fi
rm kernel-firmware-*.rpm
if ! rpm -q \$(rpm -qp kernel-*.rpm); then
    rpm -ivh --oldpackage kernel*.rpm
fi

grubby --set-default=/boot/vmlinuz-\${KERNEL_VERSION_AND_RELEASE}.x86_64

yum install -y lustre-client-modules-*.rpm lustre-client-*.rpm

# Removed and installed a kernel, so need a reboot
sync
sync
init 6
EOC
