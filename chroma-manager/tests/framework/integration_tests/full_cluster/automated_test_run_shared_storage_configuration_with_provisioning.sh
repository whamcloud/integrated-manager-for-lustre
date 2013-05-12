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

CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$(ls $PWD/shared_storage_configuration_cluster_cfg.json)"}
CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

MEASURE_COVERAGE=${MEASURE_COVERAGE:-true}
TESTS=${TESTS:-"tests/integration/shared_storage_configuration/"}
PROXY=${PROXY:-''} # Pass in a command that will set your proxy settings iff the cluster is behind a proxy. Ex: PROXY="http_proxy=foo https_proxy=foo"

echo "Beginning installation and setup..."

# Install and setup integration tests on integration test runner
scp $CLUSTER_CONFIG root@$TEST_RUNNER:/root/cluster_cfg.json
ssh root@$TEST_RUNNER <<EOF
$PROXY yum -y install chroma-manager-integration-tests
EOF

case "$HOST_IP" in
     10.10.4.29)    MCAST_START=5420 ;;   # client-29
     10.10.4.34)    MCAST_START=5480 ;;   # hydra-2
     10.10.4.36)    MCAST_START=5440 ;;   # hydra-4
    10.10.4.130)    MCAST_START=5460 ;;   # fat-intel-3
              *)    echo "I don't recognize this cluster, bailing"
                    exit 1 ;;
esac

# Install and setup chroma software storage appliances
pdsh -l root -R ssh -S -w $(spacelist_to_commalist ${STORAGE_APPLIANCES[@]}) "set -xe; exec 2>&1
yumdownloader --disablerepo=* --enablerepo=chroma kernel
rpm -ivh --oldpackage kernel*.rpm
$PROXY yum install -y chroma-agent-management

if $MEASURE_COVERAGE; then
    $PROXY yum install -y python-coverage
    cat <<\"EOF\" > /usr/lib/python2.6/site-packages/chroma_agent/.coveragerc
[run]
data_file = /var/tmp/.coverage
parallel = True
source = /usr/lib/python2.6/site-packages/chroma_agent/
EOF
    cat <<\"EOF\" > /usr/lib/python2.6/site-packages/sitecustomize.py
import coverage
cov = coverage.coverage(config_file='/usr/lib/python2.6/site-packages/chroma_agent/.coveragerc', auto_data=True)
cov.start()
cov._warn_no_data = False
cov._warn_unimported_source = False
EOF
else
    # Ensure that coverage is disabled
    rm -f /usr/lib/python2.6/site-packages/sitecustomize.py*
fi

# Configure corosync
case \$(uname -n) in
    *vm[56].lab.whamcloud.com) MCAST_PORT=$((MCAST_START+1)) ;;
    *vm[78].lab.whamcloud.com) MCAST_PORT=$((MCAST_START+3)) ;;
esac
cat <<EOF > /etc/corosync/corosync.conf
compatibility: whitetank

totem {
        version: 2
        secauth: off
        threads: 0
        interface {
                ringnumber: 0
                bindnetaddr: 10.10.4.1
                mcastaddr: 226.94.1.1
                mcastport: \$MCAST_PORT
                ttl: 1
        }
}

logging {
        fileline: off
        to_stderr: no
        to_logfile: yes
        to_syslog: yes
        logfile: /var/log/cluster/corosync.log
        debug: off
        timestamp: on
        logger_subsys {
                subsys: AMF
                debug: off
        }
}

amf {
        mode: disabled
}
service {
        name: pacemaker
        ver: 1
}
EOF
chkconfig corosync on
chkconfig pacemaker on

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

echo "MEASURE_COVERAGE: $MEASURE_COVERAGE"
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

# Configure pacemaker
# holy hackery here batman!  this is because the clustering of the nodes
# as returned by the provisioner is hard coded and the provisioner doesn't
# actually fake that for us and we are just expected to know that 5/6 and
# 7/8 are pairs
base=${STORAGE_APPLIANCES[0]%%vm*}vm
pdsh -l root -R ssh -S -w "${base}5,${base}7" "set -ex; exec 2>&1
STORAGE_APPLIANCES_${base//-/_}5=\"${base}5.lab.whamcloud.com ${base}6.lab.whamcloud.com\"
STORAGE_APPLIANCES_${base//-/_}7=\"${base}7.lab.whamcloud.com ${base}8.lab.whamcloud.com\"
# Wait for the CIB to be up (and erase it while we try)
RUNNING_TIME=0
while ! cibadmin -f -E && [ \$RUNNING_TIME -lt 500 ]; do
  let RUNNING_TIME=\$RUNNING_TIME+1
  sleep 1
done

if [ \$RUNNING_TIME -eq 500 ]; then
    echo \"Timed out waiting for CIB to start up\"
    exit 1
fi

crm configure property no-quorum-policy=\"ignore\"
crm configure property symmetric-cluster=\"true\"
crm configure property cluster-infrastructure=\"openais\"
crm configure property stonith-enabled=\"true\"
crm configure rsc_defaults resource-stickiness=1000
crm configure rsc_defaults failure-timeout=\"20m\"
crm configure rsc_defaults migration-threshold=3

hostname=\$(uname -n)
hostname=\${hostname%%%%.*}
var=\"STORAGE_APPLIANCES_\${hostname//-/_}\"
for NODE in \${!var}; do
  VM_NAME=\${NODE%%%%.*}
  SSH_ID="/root/.ssh/id_rsa"
  crm -F configure primitive st-\$NODE stonith:fence_virsh params \
                                       ipaddr=$HOST_IP login=root \
                                       identity_file="\$SSH_ID" \
                                       port=\$VM_NAME action=reboot secure=true \
                                       pcmk_host_list=\$NODE \
                                       pcmk_host_check=static-list pcmk_host_map=""

  cibadmin -o constraints -C -X \"<rsc_location id=\\\"run-st-\$NODE-anywhere\\\" rsc=\\\"st-\$NODE\\\">
    <rule id=\\\"run-st-\$NODE-anywhere-rule\\\" score=\\\"100\\\">
      <expression id=\\\"run-st-\$NODE-anywhere-expr\\\" attribute=\\\"#uname\\\" operation=\\\"ne\\\" value=\\\"\$NODE\\\"/>
    </rule>
  </rsc_location>\"
done" | dshbak -c

echo "End installation and setup."

set +e
set -x

echo "Begin running tests..."

ssh root@$TEST_RUNNER <<EOF
cd /usr/share/chroma-manager/
unset http_proxy; unset https_proxy
set -x
TEST_FILES=(\$(find $TESTS -name "test_*.py"))
for TEST_FILE in \${TEST_FILES[@]}; do
    SHORT_FILE_NAME=\$(basename \$TEST_FILE .py)
    ./tests/integration/run_tests -f -c /root/cluster_cfg.json -x ~/test_report_\$SHORT_FILE_NAME.xml \$TEST_FILE
done

# Verify we got the report for all of the tests
NUM_TEST_FILES=\${#TEST_FILES[@]}
NUM_TEST_REPORTS=\$(ls ~/test_report_*.xml | wc -l)
if [ ! \$NUM_TEST_REPORTS = \$NUM_TEST_FILES ]; then
  exit 1;
fi
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

    rpdcp -l root -R ssh -w $(spacelist_to_commalist $CHROMA_MANAGER ${STORAGE_APPLIANCES[@]}) /var/tmp/.coverage $PWD

    ssh root@$CHROMA_MANAGER chroma-config start
fi

exit 0
