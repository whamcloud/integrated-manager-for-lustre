#!/bin/sh -xe

CHROMA_MANAGER=hydra-2-lustre-1-8-chroma-manager-1
STORAGE_APPLIANCES=(hydra-2-lustre-1-8-mgs-mds hydra-2-lustre-1-8-oss1 hydra-2-lustre-1-8-oss2 hydra-2-lustre-1-8-oss3 hydra-2-lustre-1-8-oss4)
CLIENT_1=hydra-2-lustre-1-8-client
LUSTRE_SERVER_DISTRO=el5

echo "Beginning installation and setup..."

rm -rf ~/lustre_1_8_test_reports/*
rm -rf ~/lustre_1_8_coverage_reports/.coverage*
mkdir -p ~/lustre_1_8_test_reports/*
mkdir -p ~/lustre_1_8_coverage_reports/.coverage*

# Remove all old rpms from previous run
for machine in $CHROMA_MANAGER ${STORAGE_APPLIANCES[@]} $CLIENT_1; do
    ssh $machine "rm -rvf ~/rpms/*"
done

# Copy rpms to each of the machines
scp ~/lustre_1_8_rpms/arch\=x86_64\,distro\=el6/dist/chroma-manager* $CHROMA_MANAGER:~/rpms/
scp ~/lustre_1_8_requirements/requirements.txt $CHROMA_MANAGER:~/requirements.txt
for storage_appliance in ${STORAGE_APPLIANCES[@]}; do
    if [ "$LUSTRE_SERVER_DISTRO"="el5" ]; then
        scp $(ls ~/lustre_1_8_rpms/arch\=x86_64\,distro\=$LUSTRE_SERVER_DISTRO/dist/chroma-agent-* | grep -v management) $storage_appliance:~/rpms/
    else
        scp ~/lustre_1_8_rpms/arch\=x86_64\,distro\=$LUSTRE_SERVER_DISTRO/dist/chroma-agent-* $storage_appliance:~/rpms/
    fi
done

# Install and setup chroma software storage appliances
for storage_appliance in ${STORAGE_APPLIANCES[@]}; do
    ssh $storage_appliance <<EOF
    service chroma-agent stop
    set -xe
    yum remove -y chroma-agent*
    yum install -y --nogpgcheck ~/rpms/chroma-agent-*
    rm -f /var/tmp/.coverage*
    echo "
[run]
data_file = /var/tmp/.coverage
parallel = True
source = /usr/lib/python2.6/site-packages/chroma_agent/
" > /usr/lib/python2.6/site-packages/chroma_agent/.coveragerc
    echo "import coverage
cov = coverage.coverage(config_file='/usr/lib/python2.6/site-packages/chroma_agent/.coveragerc', auto_data=True)
cov.start()
" > /usr/lib/python2.6/site-packages/sitecustomize.py
    service chroma-agent start < /dev/null > /dev/null
EOF
done

# Install and setup chroma manager
ssh $CHROMA_MANAGER <<"EOF"
chroma-config stop

logrotate -fv /etc/logrotate.d/chroma-manager
yum remove -y chroma-manager*
rm -rf /usr/share/chroma-manager/

pip install --force-reinstall -r ~/requirements.txt
yum install -y ~/rpms/chroma-manager-*
echo "import logging 
LOG_LEVEL = logging.DEBUG" > /usr/share/chroma-manager/local_settings.py

rm -f /var/tmp/.coverage*
echo "
[run]
data_file = /var/tmp/.coverage
parallel = True
source = /usr/share/chroma-manager/
" > /usr/share/chroma-manager/.coveragerc
echo "import coverage
cov = coverage.coverage(config_file='/usr/share/chroma-manager/.coveragerc', auto_data=True)
cov.start()
" > /usr/lib/python2.6/site-packages/sitecustomize.py
EOF

echo "End installation and setup."
echo "Begin running tests..."

set +e

ssh $CHROMA_MANAGER <<EOF
rm -f /root/test_report.xml
cd /usr/share/chroma-manager/
set -x
nosetests --verbosity=2 tests/integration/utils/full_cluster_reset.py --tc-format=json --tc-file=/root/existing_filesystem_configuration_cluster_cfg.json
./tests/integration/run_tests -f -c ~/existing_filesystem_configuration_cluster_cfg.json -x /root/test_report.xml tests/integration/existing_filesystem_configuration/
EOF
integration_test_status=$?

echo "End running tests."

scp $CHROMA_MANAGER:/root/test_report.xml ~/lustre_1_8_test_reports/

ssh $CHROMA_MANAGER chroma-config stop

for machine in $CHROMA_MANAGER ${STORAGE_APPLIANCES[@]}; do
ssh $machine <<"EOC"
    set -x
    rm -f /usr/lib/python2.6/site-packages/sitecustomize.py*
    cd /var/tmp/
    coverage combine
EOC
scp $machine:/var/tmp/.coverage lustre_1_8_coverage_reports/.coverage.$machine
done

ssh $CHROMA_MANAGER chroma-config start

if [ $integration_test_status -ne 0 ]; then
    echo "AUTOMATED TEST RUN FAILED."
fi

exit $integration_test_status
