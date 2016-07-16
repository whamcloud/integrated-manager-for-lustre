#!/bin/bash -ex

# Upgrade the OS to the distribution name and version passed.
# In reality the distribution must by the same and the current although the version
# can be any forward version.
function upgrade_os {
    local upgrade_distro_name=${1,,}
    local upgrade_distro_version="$2"
    local comma_list_nodes="$3"

    local upgrade_distro_arch="x86_64"

    local upgrade_distro_name_version_arch="test-"${upgrade_distro_name}${upgrade_distro_version}-${upgrade_distro_arch}

    echo "Now upgrade the operating system to ${upgrade_distro_name_version_arch} on nodes ${comma_list_nodes}"

    pdsh -l root -R ssh -S -w ${comma_list_nodes} "exec 2>&1; set -xe
if [ ! -f /etc/yum.repos.d/cobbler-config.repo.orig ]; then
    cp /etc/yum.repos.d/cobbler-config.repo{,.orig}
fi

# Fetch the cobbler repo file for the version we are upgrading to, and clean the repo of
# the data form the previous repo file.
curl -o /etc/yum.repos.d/cobbler-config.repo \"http://cobbler/cblr/svc/op/yum/profile/${upgrade_distro_name_version_arch}\"
yum clean all

# On RHEL systems, we need to set the releasever
if which subscription-manager; then
    # https://access.redhat.com/support/cases/#/case/01652731
    #subscription-manager release --set=${upgrade_distro_version}
    subscription-manager release --set=6Server
fi

epel_repo=\$(yum repolist | sed -n -e 's/^\\([^ ]*[eE][pP][eE][lL][^ ]*\\).*/\\1/p')

if [ -n "\${epel_repo}" ]; then
    yum-config-manager --disable \${epel_repo}
fi

rpm -qa | sort >/tmp/before_upgrade
yum -y upgrade
rpm -qa | sort >/tmp/after_upgrade

# The yum upgrade will have restored the /etc/yum.repos.d/CentOS-*.repo
# files so remove them here
rm /etc/yum.repos.d/CentOS-*.repo

# TODO: we really ought to reboot here
#       a new kernel was surely installed and real users would reboot here" | dshbak -c

    echo "End operating system upgrade"


    # We have upgraded to the upgrade_distribution so the TEST_DISTRO_VERSION has now changed.
    export TEST_DISTRO_VERSION=${upgrade_distro_version}
}
