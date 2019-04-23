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

# Clean the yum metadata and fetch fresh data since we just changed all of the
# available repos. In addition to just wanting to be sure that the rest of the
# testing doesn't have bad cache data, the yum repolist below annoyingly
# doesn't actually cause it to fetch fresh data even after a clean, and will
# fail to parse the resulting output if the metadata has expired, so we must
# also makecache explicitly.
yum clean all
yum makecache

rpm -qa | sort >/tmp/before_upgrade

yum -y upgrade --exclude=python2-iml*

if [[ ! \$(lsb_release -r -s) =~ ${upgrade_distro_version}(\\.[0-9]*.*)?$ ]]; then
    echo \"O/S didn't actually upgrade\"
    exit 1
fi

rpm -qa | sort >/tmp/after_upgrade


# TODO: we really ought to reboot here
#       a new kernel was surely installed and real users would reboot here" | dshbak -c

    if [ ${PIPESTATUS[0]} != 0 ]; then
        return 1
    fi

    echo "End operating system upgrade"


    # We have upgraded to the upgrade_distribution so the TEST_DISTRO_VERSION has now changed.
    export TEST_DISTRO_VERSION=${upgrade_distro_version}

}
