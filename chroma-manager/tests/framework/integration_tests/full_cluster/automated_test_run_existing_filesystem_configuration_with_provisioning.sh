#!/bin/sh -ex

spacelist_to_commalist() {
    echo $@ | tr ' ' ','
}

[ -r localenv ] && . localenv

# Remove test results and coverage reports from previous run
rm -rfv $PWD/test_reports/*
rm -rfv $PWD/coverage_reports/.coverage*
mkdir -p $PWD/test_reports
mkdir -p $PWD/coverage_reports

CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$(ls $PWD/existing_filesystem_configuration_cluster_cfg.json)"}
CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

MEASURE_COVERAGE=${MEASURE_COVERAGE:-true}
TESTS=${TESTS:-"tests/integration/existing_filesystem_configuration/"}
PROXY=${PROXY:-''} # Pass in a command that will set your proxy settings iff the cluster is behind a proxy. Ex: PROXY="http_proxy=foo https_proxy=foo"

echo "Beginning installation and setup..."

# Install and setup integration tests on integration test runner
scp $CLUSTER_CONFIG root@$TEST_RUNNER:/root/cluster_cfg.json
ssh root@$TEST_RUNNER <<EOF
$PROXY yum -y install chroma-manager-integration-tests
EOF

# Install and setup chroma software storage appliances
pdsh -l root -R ssh -S -w $(spacelist_to_commalist ${STORAGE_APPLIANCES[@]}) "set -xe; exec 2>&1
yumdownloader --disablerepo=* --enablerepo=chroma kernel
rpm -ivh --oldpackage kernel*.rpm
$PROXY yum install -y chroma-agent

if $MEASURE_COVERAGE; then
    $PROXY yum install -y python-coverage
    cat <<\"EOF\" > /usr/lib/python2.6/site-packages/.coveragerc
[run]
data_file = /var/tmp/.coverage
parallel = True
source = /usr/lib/python2.6/site-packages/chroma_agent/
EOF
    cat <<\"EOF\" > /usr/lib/python2.6/site-packages/sitecustomize.py
import coverage
cov = coverage.coverage(config_file='/usr/lib/python2.6/site-packages/.coveragerc', auto_data=True)
cov.start()
cov._warn_no_data = False
cov._warn_unimported_source = False
EOF
else
    # Ensure that coverage is disabled
    rm -f /usr/lib/python2.6/site-packages/sitecustomize.py*
fi

# Removed and installed a kernel, so need a reboot
sync
sync
init 6" | dshbak -c

# Install and setup chroma manager
ssh root@$CHROMA_MANAGER <<EOF
set -ex
$PROXY yum install -y chroma-manager

cat <<"EOF1" > /usr/share/chroma-manager/local_settings.py
import logging
LOG_LEVEL = logging.DEBUG
EOF1

if $MEASURE_COVERAGE; then
    $PROXY yum install -y python-coverage
    cat <<"EOF1" > /usr/share/chroma-manager/.coveragerc
[run]
data_file = /var/tmp/.coverage
parallel = True
source = /usr/share/chroma-manager/
EOF1
    cat <<"EOF1" > /usr/lib/python2.6/site-packages/sitecustomize.py
import coverage
cov = coverage.coverage(config_file='/usr/share/chroma-manager/.coveragerc', auto_data=True)
cov.start()
cov._warn_no_data = False
cov._warn_unimported_source = False
EOF1
else
    # Ensure that coverage is disabled
    rm -f /usr/lib/python2.6/site-packages/sitecustomize.py*
fi
EOF

# wait for rebooted nodes
sleep 5
nodes="${STORAGE_APPLIANCES[@]}"
RUNNING_TIME=0
while [ -n "$nodes" ] && [ $RUNNING_TIME -lt 500 ]; do
    for node in $nodes; do
        if ssh root@$node id; then
            nodes=$(echo "$nodes" | sed -e "s/$node//" -e 's/^ *//' -e 's/ *$//')
        fi
    done
    (( RUNNING_TIME++ )) || true
    sleep 1
done

# Create a lustre filesystem outside of Chroma
ssh root@$TEST_RUNNER <<EOF
cd /usr/share/chroma-manager/
unset http_proxy; unset https_proxy
./tests/integration/run_tests -f -c /root/cluster_cfg.json tests/integration/existing_filesystem_configuration/utils/create_lustre_filesystem.py
EOF

echo "End installation and setup."

set +e
set -x

echo "Begin running tests..."

ssh root@$TEST_RUNNER <<EOF
cd /usr/share/chroma-manager/
unset http_proxy; unset https_proxy
set -x
./tests/integration/run_tests -f -c /root/cluster_cfg.json -x ~/test_report.xml $TESTS
EOF

echo "End running tests."
echo "Collecting reports..."

scp root@$TEST_RUNNER:~/test_report*.xml $PWD/test_reports/

if $MEASURE_COVERAGE; then
    ssh root@$CHROMA_MANAGER chroma-config stop

    pdsh -l root -R ssh -S -w $(spacelist_to_commalist $CHROMA_MANAGER ${STORAGE_APPLIANCES[@]}) "set -x
      rm -f /usr/lib/python2.6/site-packages/sitecustomize.py*
      cd /var/tmp/
      coverage combine" | dshbak -c

    for SERVER in $CHROMA_MANAGER ${STORAGE_APPLIANCES[@]}; do
        scp $SERVER:/var/tmp/.coverage .coverage.$SERVER
    done 

    ssh root@$CHROMA_MANAGER chroma-config start
fi

exit 0
