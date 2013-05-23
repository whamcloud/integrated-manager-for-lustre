#!/bin/bash -ex

spacelist_to_commalist() {
    echo $@ | tr ' ' ','
}

[ -r localenv ] && . localenv

# Remove test results and coverage reports from previous run
rm -rfv $PWD/test_reports/*
rm -rfv $PWD/coverage_reports/.coverage*
mkdir -p $PWD/test_reports
mkdir -p $PWD/coverage_reports

CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$(ls $PWD/shared_storage_configuration_cluster_cfg.json)"}
CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}
USE_FENCE_XVM=false

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

# TODO: figure out how coverage fits into all of this new world order
#MEASURE_COVERAGE=${MEASURE_COVERAGE:-true}
MEASURE_COVERAGE=false
TESTS=${TESTS:-"tests/integration/shared_storage_configuration/"}
PROXY=${PROXY:-''} # Pass in a command that will set your proxy settings iff the cluster is behind a proxy. Ex: PROXY="http_proxy=foo https_proxy=foo"

echo "Beginning installation and setup..."

# put some keys on the nodes for easy access by developers
pdsh -l root -R ssh -S -w $(spacelist_to_commalist $ALL_NODES) "exec 2>&1; set -xe
cat <<\"EOF\" >> /root/.ssh/authorized_keys
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCrcI6x6Fv2nzJwXP5mtItOcIDVsiD0Y//LgzclhRPOT9PQ/jwhQJgrggPhYr5uIMgJ7szKTLDCNtPIXiBEkFiCf9jtGP9I6wat83r8g7tRCk7NVcMm0e0lWbidqpdqKdur9cTGSOSRMp7x4z8XB8tqs0lk3hWefQROkpojzSZE7fo/IT3WFQteMOj2yxiVZYFKJ5DvvjdN8M2Iw8UrFBUJuXv5CQ3xV66ZvIcYkth3keFk5ZjfsnDLS3N1lh1Noj8XbZFdSRC++nbWl1HfNitMRm/EBkRGVP3miWgVNfgyyaT9lzHbR8XA7td/fdE5XrTpc7Mu38PE7uuXyLcR4F7l brian@brian-laptop
EOF" | dshbak -c
if [ ${PIPESTATUS[0]} != 0 ]; then
    exit 1
fi

# need to remove the chroma repositories configured by the provisioner
pdsh -l root -R ssh -S -w $(spacelist_to_commalist $CHROMA_MANAGER ${STORAGE_APPLIANCES[@]}) "exec 2>&1; set -xe
rm -f /etc/yum.repos.d/autotest.repo" | dshbak -c
if [ ${PIPESTATUS[0]} != 0 ]; then
    exit 1
fi

# Install and setup integration tests on integration test runner
scp $CLUSTER_CONFIG root@$TEST_RUNNER:/root/cluster_cfg.json
ssh root@$TEST_RUNNER <<EOF
exec 2>&1; set -xe
# need to substitute in the el6.4 repo until this is all transitioned over
sed -i -e 's/\(distro=el6\)\//\1.4\//' /etc/yum.repos.d/autotest.repo
yum --disablerepo=\* --enablerepo=chroma makecache
$PROXY yum -y install chroma-manager-integration-tests

if $USE_FENCE_XVM; then
    # make sure the host has fence_virtd installed and configured
    ssh root@$HOST_IP "exec 2>&1; set -xe
    uname -a
    yum install -y fence-virt fence-virtd fence-virtd-libvirt fence-virtd-multicast
    mkdir -p /etc/cluster
    echo \"not secure\" > /etc/cluster/fence_xvm.key
    restorecon -Rv /etc/cluster/
    cat <<\"EOF1\" > /etc/fence_virt.conf
backends {
	libvirt {
		uri = \"qemu:///system\";
	}

}

listeners {
	multicast {
		port = \"1229\";
		family = \"ipv4\";
		address = \"225.0.0.12\";
		key_file = \"/etc/cluster/fence_xvm.key\";
		interface = \"virbr0\";
	}

}

fence_virtd {
	module_path = \"/usr/lib64/fence-virt\";
	backend = \"libvirt\";
	listener = \"multicast\";
}
EOF1
    chkconfig --add fence_virtd
    chkconfig fence_virtd on
    service fence_virtd restart"
fi
EOF

# Install and setup chroma software storage appliances
pdsh -l root -R ssh -S -w $(spacelist_to_commalist ${STORAGE_APPLIANCES[@]}) "exec 2>&1; set -xe
# this can't be done here anymore since package installation is done
# as part of adding storage servers to the manager
#if $MEASURE_COVERAGE; then
#    $PROXY yum install -y python-coverage
#    cat <<\"EOF\" > /usr/lib/python2.6/site-packages/chroma_agent/.coveragerc
#[run]
#data_file = /var/tmp/.coverage
#parallel = True
#source = /usr/lib/python2.6/site-packages/chroma_agent/
#EOF
#    cat <<\"EOF\" > /usr/lib/python2.6/site-packages/sitecustomize.py
#import coverage
#cov = coverage.coverage(config_file='/usr/lib/python2.6/site-packages/chroma_agent/.coveragerc', auto_data=True)
#cov.start()
#cov._warn_no_data = False
#cov._warn_unimported_source = False
#EOF
#else
#    # Ensure that coverage is disabled
#    rm -f /usr/lib/python2.6/site-packages/sitecustomize.py*
#fi

if $USE_FENCE_XVM; then
    # fence_xvm support
    mkdir -p /etc/cluster
    echo \"not secure\" > /etc/cluster/fence_xvm.key
fi" | dshbak -c
if [ ${PIPESTATUS[0]} != 0 ]; then
    exit 1
fi

# Install and setup chroma manager
scp chroma.tar.gz root@$CHROMA_MANAGER:/tmp
ssh root@$CHROMA_MANAGER "exec 2>&1; set -ex
# Install from the installation package
cd /tmp
tar xzvf chroma.tar.gz
./install.sh <<EOF1
$CHROMA_USER
$CHROMA_EMAIL
$CHROMA_PASS
$CHROMA_PASS
${CHROMA_NTP_SERVER:-localhost}
EOF1

cat <<\"EOF1\" > /usr/share/chroma-manager/local_settings.py
import logging
LOG_LEVEL = logging.DEBUG
EOF1

echo \"MEASURE_COVERAGE: $MEASURE_COVERAGE\"
if $MEASURE_COVERAGE; then
    $PROXY yum install -y python-coverage
    cat <<\"EOF1\" > /usr/share/chroma-manager/.coveragerc
[run]
data_file = /var/tmp/.coverage
parallel = True
source = /usr/share/chroma-manager/
EOF1
    cat <<\"EOF1\" > /usr/lib/python2.6/site-packages/sitecustomize.py
import coverage
cov = coverage.coverage(config_file='/usr/share/chroma-manager/.coveragerc', auto_data=True)
cov.start()
cov._warn_no_data = False
cov._warn_unimported_source = False
EOF1
else
    # Ensure that coverage is disabled
    rm -f /usr/lib/python2.6/site-packages/sitecustomize.py*
fi"

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
      coverage combine
      yum -y install pdsh" | dshbak -c
    if [ ${PIPESTATUS[0]} != 0 ]; then
        exit 1
    fi

    rpdcp -l root -R ssh -w $(spacelist_to_commalist $CHROMA_MANAGER ${STORAGE_APPLIANCES[@]}) /var/tmp/.coverage $PWD

    ssh root@$CHROMA_MANAGER chroma-config start
fi

exit 0
