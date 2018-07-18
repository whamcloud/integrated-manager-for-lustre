# Remove test results and coverage reports from previous run
rm -rfv $PWD/test_reports/*
rm -rfv $PWD/coverage_reports/.coverage*
mkdir -p $PWD/test_reports
mkdir -p $PWD/coverage_reports

CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$(ls $PWD/shared_storage_configuration_cluster_cfg.json)"}
CHROMA_DIR=${CHROMA_DIR:-"$PWD/intel-manager-for-lustre/"}
USE_FENCE_XVM=false

eval $(python $CHROMA_DIR/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

MEASURE_COVERAGE=${MEASURE_COVERAGE:-true}
PROXY=${PROXY:-''} # Pass in a command that will set your proxy settings iff the cluster is behind a proxy. Ex: PROXY="http_proxy=foo https_proxy=foo"

echo "Beginning installation and setup..."

# put some keys on the nodes for easy access by developers
# and make sure EPEL is enabled
pdsh -l root -R ssh -S -w $(spacelist_to_commalist $ALL_NODES) "exec 2>&1; set -xe
$LOCAL_CLUSTER_SETUP

# disable the toolkit repo
yum-config-manager --disable local-toolkit_el7-x86_64

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

if [ -n "$CLIENT_1" ] && [[ \${HOSTNAME%%%.*} = ${CLIENT_1%%.*} ]]; then
    yum-config-manager --add-repo "$LUSTRE_CLIENT_URL"
    sed -i -e '1d' -e \"2s/^.*$/[lustre-client]/\" -e '/baseurl/s/,/%2C/g' -e '/enabled/a gpgcheck=0' "$LUSTRE_CLIENT_REPO_FILE"
fi" | dshbak -c
if [ ${PIPESTATUS[0]} != 0 ]; then
    exit 1
fi