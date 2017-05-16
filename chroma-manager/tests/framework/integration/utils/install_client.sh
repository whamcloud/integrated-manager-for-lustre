# Install the IEEL Lustre client
ssh root@$CLIENT_1 "exec 2>&1; set -xe

mkdir lustre_client_rpms
cd lustre_client_rpms

# Add the client repo
cat << EOF > /etc/yum.repos.d/lustre-client.repo
[lustre-client]
name=lustre-client
baseurl=https://build.whamcloud.com/job/lustre-master/lastSuccessfulBuild/arch=x86_64%2Cbuild_type=client%2Cdistro=el\\\$releasever%2Cib_stack=inkernel/artifact/artifacts/
enabled=1
sslverify=0
gpgcheck=0
EOF

# it is tempting to just use:
#   yum install --exclude=kernel-debug -y lustre-client-modules lustre-client
#   KERNEL_VERSION_AND_RELEASE=\"\$(rpm -qR lustre-client-modules | sed -n -e '/^kernel =/s/.* = //p')\";
# here, however if a newer kernel than what the Lustre client wants is
# installed then yum complains and refuses to install the older kernel
# pity

yumdownloader lustre-client lustre-client-modules

# Extract what kernel version and release we need to match the client rpms
# rpm -qpr will list the dependencies of the rpm, and the sed strips out the
# other dependencies and the 'kernel = ' at the beggining of the line.
KERNEL_VERSION_AND_RELEASE=\"\$(rpm -qpR lustre-client-modules-* | sed -n -e '/^kernel =/s/.* = //p')\";

yum -y install redhat-lsb-core

if [[ \$(lsb_release -sr) = 6.* ]]; then
    yumdownloader kernel-firmware-\$KERNEL_VERSION_AND_RELEASE

    if ! rpm -q \$(rpm -qp kernel-firmware-*.rpm); then
        rpm -Uvh --oldpackage kernel-firmware-*.rpm
    fi
    rm kernel-firmware-*.rpm
fi

yumdownloader kernel-\$KERNEL_VERSION_AND_RELEASE # Have to install explicitly to avoid getting kernel-debug in the automatic dependency resolution

if ! rpm -q \$(rpm -qp kernel-*.rpm); then
    rpm -ivh --oldpackage kernel*.rpm
fi

grubby --set-default=/boot/vmlinuz-\${KERNEL_VERSION_AND_RELEASE}.x86_64

yum install -y lustre-client-modules-*.rpm lustre-client-*.rpm

# Removed and installed a kernel, so need a reboot
sync
sync
nohup bash -c \"sleep 2; init 6\" >/dev/null 2>/dev/null </dev/null & exit 0"

