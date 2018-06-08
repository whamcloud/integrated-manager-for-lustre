#!/bin/bash

# Install the Lustre client

# shellcheck disable=SC1090
. "$CHROMA_DIR"/tests/framework/integration/utils/reboot_node.sh

# shellcheck disable=SC2029
ssh root@"$CLIENT_1" "exec 2>&1; set -xe
# set up required repos
yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/$COPR_OWNER/$COPR_PROJECT/repo/epel-7/$COPR_OWNER-$COPR_PROJECT-epel-7.repo

# DNF is smarter than YUM
yum -y install dnf

# avoid getting the kernel-debug RPM
dnf -y install --exclude kernel-debug lustre-client

# see if we installed the kmod or the dkms version
# only (possibly) need to reboot for the kmod client
if rpm -q kmod-lustre-client; then
    # see if we need to reboot into a new kernel
    req_kernel=\$(rpm -q --requires kmod-lustre-client | sed -ne 's/kernel >= \(.*\)/\1/p')

    if [[ \$(uname -r) != \$req_kernel* ]]; then
        KERNEL_VERSION_AND_RELEASE=\$(rpm -q kernel-\$req_kernel* |
                                      sed -ne \"1s/.*\\\(\$req_kernel.*\\\)\.[^\.]*/\1/p\")

        grubby --set-default=/boot/vmlinuz-\${KERNEL_VERSION_AND_RELEASE}.x86_64

        # Removed and installed a kernel, so need a reboot
        $REBOOT_NODE
    fi
fi"
