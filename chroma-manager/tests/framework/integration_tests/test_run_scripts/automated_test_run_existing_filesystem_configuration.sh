#!/bin/sh -xe

CHROMA_MANAGER=${CHROMA_MANAGER:-'hydra-2-lustre-1-8-chroma-manager-1'}
STORAGE_APPLIANCES=${STORAGE_APPLIANCES:-'hydra-2-lustre-1-8-mgs-mds hydra-2-lustre-1-8-oss1 hydra-2-lustre-1-8-oss2 hydra-2-lustre-1-8-oss3 hydra-2-lustre-1-8-oss4'}
CLIENT_1=${CLIENT_1:-'hydra-2-lustre-1-8-client'}
LUSTRE_SERVER_DISTRO=${LUSTRE_SERVER_DISTRO:-'el5'}
PYTHON_VERSION=${PYTHON_VERSION:-'2.4'}
TEST_RUNNER=${TEST_RUNNER:-'hydra-2-lustre-1-8-chroma-manager-1'}
MEASURE_COVERAGE=${MEASURE_COVERAGE:-true}

echo "Beginning installation and setup..."

rm -rf ~/efs/test_reports/*
rm -rf ~/efs/coverage_reports/.coverage*
mkdir -p ~/efs/test_reports/*
mkdir -p  ~/efs/coverage_reports/

# Remove all old rpms from previous run
for machine in $CHROMA_MANAGER ${STORAGE_APPLIANCES[@]} $CLIENT_1; do
    ssh $machine "mkdir -p ~/rpms/; rm -rvf ~/rpms/*"
done

# Copy rpms to each of the machines
scp $(ls ~/efs/rpms/arch\=x86_64\,distro\=el6/dist/chroma-manager-*| grep -v integration-tests) $CHROMA_MANAGER:~/rpms/
scp ~/efs/requirements.txt $CHROMA_MANAGER:~/requirements.txt
scp ~/efs/rpms/arch\=x86_64\,distro\=el6/dist/chroma-manager-integration-tests* $TEST_RUNNER:~/rpms/
scp ~/efs/requirements.txt $TEST_RUNNER:~/requirements.txt
for storage_appliance in ${STORAGE_APPLIANCES[@]}; do
    scp $(ls ~/efs/rpms/arch\=x86_64\,distro\=$LUSTRE_SERVER_DISTRO/dist/chroma-agent-* | grep -v management) $storage_appliance:~/rpms/
done

# Install and setup chroma software storage appliances
for storage_appliance in ${STORAGE_APPLIANCES[@]}; do
    ssh $storage_appliance <<EOF
    service chroma-agent stop
echo "compress

/var/log/chroma*.log {
        missingok
        rotate 10
        nocreate
        size=10M
}" > /etc/logrotate.d/chroma-agent
    logrotate -fv /etc/logrotate.d/chroma-agent
    logrotate -fv /etc/logrotate.d/syslog

    set -xe
    yum remove -y chroma-agent*
    yum install -y --nogpgcheck ~/rpms/chroma-agent-*

    rm -f /var/tmp/.coverage*
    if $MEASURE_COVERAGE; then
      set +e
      yum install -y python-pip
      pip-python install --upgrade pip
      pip-python uninstall coverage <<EOC
y
EOC
      pip-python install --force-reinstall http://github.com/kprantis/coverage/tarball/master#egg=coverage
      set -e
      echo "
[run]
data_file = /var/tmp/.coverage
parallel = True
source = /usr/lib/python$PYTHON_VERSION/site-packages/chroma_agent/
" > /usr/lib/python$PYTHON_VERSION/site-packages/chroma_agent/.coveragerc
    echo "import coverage
cov = coverage.coverage(config_file='/usr/lib/python$PYTHON_VERSION/site-packages/chroma_agent/.coveragerc', auto_data=True)
cov.start()
cov._warn_no_data = False
cov._warn_unimported_source = False
" > /usr/lib/python$PYTHON_VERSION/site-packages/sitecustomize.py
    else
        # Ensure that coverage is disabled
        rm -f /usr/lib/python2.6/site-packages/sitecustomize.py*
    fi
    service chroma-agent start < /dev/null > /dev/null
EOF
done

# Install and setup chroma manager
ssh $CHROMA_MANAGER <<"EOF"
chroma-config stop

logrotate -fv /etc/logrotate.d/chroma-manager
logrotate -fv /etc/logrotate.d/syslog
logrotate -fv /etc/logrotate.d/rabbitmq-server

yum remove -y chroma-manager*
rm -rf /usr/share/chroma-manager/

echo "drop database chroma; create database chroma" | mysql -u root
service postgresql stop
rm -fr /var/lib/pgsql/data/*

pip-python uninstall coverage <<EOC
y
EOC
pip install --force-reinstall -r ~/requirements.txt <<EOC
s

EOC
yum install -y ~/rpms/chroma-manager-*
echo "import logging 
LOG_LEVEL = logging.DEBUG" > /usr/share/chroma-manager/local_settings.py

rm -f /var/tmp/.coverage*
if $MEASURE_COVERAGE; then
  echo "
[run]
data_file = /var/tmp/.coverage
parallel = True
source = /usr/share/chroma-manager/
" > /usr/share/chroma-manager/.coveragerc
echo "import coverage
cov = coverage.coverage(config_file='/usr/share/chroma-manager/.coveragerc', auto_data=True)
cov.start()
cov._warn_no_data = False
cov._warn_unimported_source = False
" > /usr/lib/python2.6/site-packages/sitecustomize.py
else
  # Ensure that coverage is disabled
  rm -f /usr/lib/python2.6/site-packages/sitecustomize.py*
fi
EOF

ssh $TEST_RUNNER <<EOF
yum remove -y chroma-manager-integration-tests*

echo "drop database test_chroma;" | mysql -u root

pip install --force-reinstall -r ~/requirements.txt <<EOC
s

EOC
yum install -y ~/rpms/chroma-manager-integration-tests*
echo "import logging 
LOG_LEVEL = logging.DEBUG" > /usr/share/chroma-manager/local_settings.py
EOF

echo "End installation and setup."
echo "Begin running tests..."

set +e

ssh $TEST_RUNNER <<EOF
rm -f /root/test_report.xml
cd /usr/share/chroma-manager/
set -x
nosetests --verbosity=2 tests/integration/utils/full_cluster_reset.py --tc-format=json --tc-file=/root/existing_filesystem_configuration_cluster_cfg.json
./tests/integration/run_tests -f -c ~/existing_filesystem_configuration_cluster_cfg.json -x /root/test_report.xml tests/integration/existing_filesystem_configuration/
EOF
integration_test_status=$?

echo "End running tests."

if $MEASURE_COVERAGE; then
  scp $TEST_RUNNER:/root/test_report.xml ~/efs/test_reports/

  ssh $CHROMA_MANAGER chroma-config stop
  ssh $CHROMA_MANAGER rm -f /usr/lib/python2.6/site-packages/sitecustomize.py*

  for machine in $CHROMA_MANAGER ${STORAGE_APPLIANCES[@]}; do
    ssh $machine <<"EOC"
      set -x
      rm -f /usr/lib/python$PYTHON_VERSION/site-packages/sitecustomize.py*
      cd /var/tmp/
      coverage combine
EOC
    scp $machine:/var/tmp/.coverage efs/coverage_reports/.coverage.$machine
  done

  ssh $CHROMA_MANAGER chroma-config start
fi

if [ $integration_test_status -ne 0 ]; then
    echo "AUTOMATED TEST RUN FAILED."
fi

exit $integration_test_status
