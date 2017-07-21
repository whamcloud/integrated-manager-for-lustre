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

if [[ \$HOSTNAME = *vm*2 ]]; then
    build_type=client
    #yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/managerforlustre/lustre-client/repo/epel-7/managerforlustre-lustre-\$build_type-epel-7.repo
    #rpm --import https://copr-be.cloud.fedoraproject.org/results/managerforlustre/manager-for-lustre/pubkey.gpg
    yum-config-manager --add-repo https://build.whamcloud.com/lustre-reviews/configurations/axis-arch/\\\$basearch/axis-build_type/client/axis-distro/el7/axis-ib_stack/inkernel/builds/49006/archive/artifacts/
    ed /etc/yum.repos.d/build.whamcloud.com_lustre-reviews_configurations_axis-arch_\\\$basearch_axis-build_type_client_axis-distro_el7_axis-ib_stack_inkernel_builds_48896_archive_artifacts_.repo << EOF
1d
1s/\\\\\$//g
/^$/i
gpgcheck=0
.
wq
EOF
fi

$LOCAL_CLUSTER_SETUP" | dshbak -c
if [ ${PIPESTATUS[0]} != 0 ]; then
    exit 1
fi
