# Remove test results and coverage reports from previous run
rm -rfv $PWD/test_reports/*
rm -rfv $PWD/coverage_reports/.coverage*
mkdir -p $PWD/test_reports
mkdir -p $PWD/coverage_reports

CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$(ls $PWD/shared_storage_configuration_cluster_cfg.json)"}
CHROMA_DIR=${CHROMA_DIR:-"$PWD/intel-manager-for-lustre/"}
USE_FENCE_XVM=false

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

MEASURE_COVERAGE=${MEASURE_COVERAGE:-true}
PROXY=${PROXY:-''} # Pass in a command that will set your proxy settings iff the cluster is behind a proxy. Ex: PROXY="http_proxy=foo https_proxy=foo"

echo "Beginning installation and setup..."

# put some keys on the nodes for easy access by developers
# and make sure EPEL is enabled
pdsh -l root -R ssh -S -w $(spacelist_to_commalist $ALL_NODES) "exec 2>&1; set -xe
cat <<\"EOF\" >> /root/.ssh/authorized_keys
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCrcI6x6Fv2nzJwXP5mtItOcIDVsiD0Y//LgzclhRPOT9PQ/jwhQJgrggPhYr5uIMgJ7szKTLDCNtPIXiBEkFiCf9jtGP9I6wat83r8g7tRCk7NVcMm0e0lWbidqpdqKdur9cTGSOSRMp7x4z8XB8tqs0lk3hWefQROkpojzSZE7fo/IT3WFQteMOj2yxiVZYFKJ5DvvjdN8M2Iw8UrFBUJuXv5CQ3xV66ZvIcYkth3keFk5ZjfsnDLS3N1lh1Noj8XbZFdSRC++nbWl1HfNitMRm/EBkRGVP3miWgVNfgyyaT9lzHbR8XA7td/fdE5XrTpc7Mu38PE7uuXyLcR4F7l brian@brian-laptop
EOF
# instruct any caching proxies to only cache packages
yum -y install ed
ed /etc/yum.conf <<EOF
/^$/i
http_caching=packages
.
wq
EOF
for key in CentOS-7 redhat-release; do
    if [ -f /etc/pki/rpm-gpg/RPM-GPG-KEY-\$key ]; then
        rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-\$key
    fi
done
yum-config-manager --enable addon-epel\$(rpm --eval %rhel)-x86_64
if ! yum repolist | grep addon-epel; then
    yum -y install epel-release
fi
yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/managerforlustre/manager-for-lustre/repo/epel-7/managerforlustre-manager-for-lustre-epel-7.repo
yum-config-manager --add-repo http://mirror.centos.org/centos/7/extras/x86_64/
yum -y install ed
ed <<EOF /etc/yum.repos.d/mirror.centos.org_centos_7_extras_x86_64_.repo
/enabled/a
gpgcheck=1
gpgkey=http://mirror.centos.org/centos/RPM-GPG-KEY-CentOS-7
.
wq
EOF
if [[ \$HOSTNAME = *vm*[29] ]]; then
    build_type=client
    yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/managerforlustre/lustre-client/repo/epel-7/managerforlustre-lustre-\$build_type-epel-7.repo
else
    build_type=server
    yum-config-manager --add-repo https://build.whamcloud.com/lustre-b2_10_last_successful/
    sed -i -e '1d' -e '2s/^.*$/[lustre]/' -e '/baseurl/s/,/%2C/g' -e '/enabled/a gpgcheck=0' /etc/yum.repos.d/build.whamcloud.com_lustre-b2_10_last_successful_.repo
fi
yum-config-manager --add-repo https://build.whamcloud.com/job/e2fsprogs-master/arch=x86_64,distro=el7/lastSuccessfulBuild/artifact/_topdir/RPMS/
sed -i -e '1d' -e '2s/^.*$/[e2fsprogs]/' -e '/baseurl/s/,/%2C/g' -e '/enabled/a gpgcheck=0' /etc/yum.repos.d/build.whamcloud.com_job_e2fsprogs-master_arch\=x86_64\,distro\=el7_lastSuccessfulBuild_artifact__topdir_RPMS_.repo
yum -y install distribution-gpg-keys-copr
if ! ls /usr/share/distribution-gpg-keys/copr/copr-*manager-for-lustre*; then
    rpm --import https://copr-be.cloud.fedoraproject.org/results/managerforlustre/manager-for-lustre/pubkey.gpg
fi
$LOCAL_CLUSTER_SETUP" | dshbak -c
if [ ${PIPESTATUS[0]} != 0 ]; then
    exit 1
fi
