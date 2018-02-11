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
if $JENKINS; then
    if [ ! -f /etc/yum.repos.d/cobbler-config.repo.orig ]; then
        cp /etc/yum.repos.d/cobbler-config.repo{,.orig}
    fi

    # Fetch the cobbler repo file for the version we are upgrading to, and clean the repo of
    # the data form the previous repo file.
    curl -o /etc/yum.repos.d/cobbler-config.repo \"http://cobbler/cblr/svc/op/yum/profile/${upgrade_distro_name_version_arch}\"
fi

# On RHEL systems, we need to set the releasever
if which subscription-manager; then
    # The way RHEL does their repos, the release for the specific minor version
    # only exists once there are updates for that version. In the small window
    # between a minor version GAing and its first updates, then there is only
    # the more generic 6Server or 7Server release. So we first test if a minor
    # version exists yet, and if so use that, but if not, use the more generic
    # [67]Server. This allows us to 'pin' older OS versions, but not break if in
    # the window between GA and first updates.
    if subscription-manager release --list | grep ${upgrade_distro_version}; then
        release=${upgrade_distro_version}
    else
        release=${upgrade_distro_version%%.*}Server
    fi
    subscription-manager release --set=\${release}
fi

# Clean the yum metadata and fetch fresh data since we just changed all of the
# available repos. In addition to just wanting to be sure that the rest of the
# testing doesn't have bad cache data, the yum repolist below annoyingly
# doesn't actually cause it to fetch fresh data even after a clean, and will
# fail to parse the resulting output if the metadata has expired, so we must
# also makecache explicitly.
yum clean all
yum makecache

yum-config-manager --disable *[eE][pP][eE][lL]*

rpm -qa | sort >/tmp/before_upgrade
yum -y upgrade

if [[ ! \$(lsb_release -r -s) =~ ${upgrade_distro_version}(\\.[0-9]*.*)?$ ]]; then
    echo \"O/S didn't actually upgrade\"
    exit 1
fi

rpm -qa | sort >/tmp/after_upgrade

if $JENKINS; then
    # The yum upgrade might have restored the /etc/yum.repos.d/CentOS-*.repo
    # files so remove them here
    if ls /etc/yum.repos.d/CentOS-*.repo; then
        rm /etc/yum.repos.d/CentOS-*.repo
    fi
fi

# TODO: we really ought to reboot here
#       a new kernel was surely installed and real users would reboot here" | dshbak -c

    if [ ${PIPESTATUS[0]} != 0 ]; then
        return 1
    fi

    echo "End operating system upgrade"


    # We have upgraded to the upgrade_distribution so the TEST_DISTRO_VERSION has now changed.
    export TEST_DISTRO_VERSION=${upgrade_distro_version}

}
