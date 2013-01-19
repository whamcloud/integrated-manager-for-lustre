#!/bin/sh -e

set +x

CHROMA_MANAGER=hydra-2-ss2-chroma-manager-1
STORAGE_APPLIANCES=(hydra-2-ss2-storage-appliance-1 hydra-2-ss2-storage-appliance-2 hydra-2-ss2-storage-appliance-3 hydra-2-ss2-storage-appliance-4)
CLIENT_1=hydra-2-ss2-client-1

echo "Beginning installation and setup..."

# Remove all old rpms from previous run
for machine in $CHROMA_MANAGER ${STORAGE_APPLIANCES[@]} $CLIENT_1; do
    ssh $machine "rm -rvf ~/rpms/*"
done

# Copy rpms to each of the machines
scp $(ls ~/ss_rpms/arch\=x86_64\,distro\=el6/dist/chroma-manager-*| grep -v integration-tests) $CHROMA_MANAGER:~/rpms/
scp ss_requirements/requirements.txt $CHROMA_MANAGER:~/requirements.txt
scp ss_requirements/requirements.txt $CLIENT_1:~/requirements.txt
scp ~/ss_rpms/arch\=x86_64\,distro\=el6/dist/chroma-manager-integration-tests* $CLIENT_1:~/rpms/
for storage_appliance in ${STORAGE_APPLIANCES[@]}; do
    scp ~/ss_rpms/arch\=x86_64\,distro\=el6/dist/chroma-agent-* $storage_appliance:~/rpms/
done

# Install and setup integration tests on integration test runner
ssh $CLIENT_1 <<EOF
cd /usr/share/chroma-manager/
nosetests --verbosity=2 tests/integration/utils/full_cluster_reset.py --tc-format=json --tc-file=/root/shared_storage_configuration_cluster_cfg.json
cd
yum remove -y chroma-manager*
rm -rf /usr/share/chroma-manager/
pip install --force-reinstall -r ~/requirements.txt
logrotate -fv /etc/logrotate.d/syslog
rm -f /var/log/chroma_test.log
yum install -y ~/rpms/chroma-manager-integration-tests*
EOF

# Install and setup chroma software storage appliances
for storage_appliance in ${STORAGE_APPLIANCES[@]}; do
    ssh $storage_appliance <<EOF
    service chroma-agent stop
    logrotate -fv /etc/logrotate.d/syslog
    set -xe
    yum remove -y chroma-agent*
    yum install -y ~/rpms/chroma-agent-*
    service chroma-agent restart
EOF
done

# Install and setup chroma manager
ssh $CHROMA_MANAGER <<"EOF"
chroma-config stop
rm -f /var/run/chroma*
logrotate -fv /etc/logrotate.d/chroma-manager
logrotate -fv /etc/logrotate.d/syslog
yum remove -y chroma-manager*
rm -rf /usr/share/chroma-manager/
echo "drop database chroma; create database chroma;" | mysql -u root
pip install --force-reinstall -r ~/requirements.txt
yum install -y ~/rpms/chroma-manager-*
echo "import logging 
LOG_LEVEL = logging.DEBUG" > /usr/share/chroma-manager/local_settings.py
EOF

echo "End installation and setup."
echo "Begin running tests..."

set +e
set -x

ssh $CLIENT_1 <<EOF
rm -f /root/test_report.xml
cd /usr/share/chroma-manager/
./tests/integration/run_tests -f -c ~/shared_storage_configuration_cluster_cfg.json -x ~/test_report.xml tests/integration/shared_storage_configuration/
EOF
integration_test_status=$?

scp $CLIENT_1:~/test_report.xml ss_test_reports/

echo "End running tests."

if [ $integration_test_status -ne 0 ]; then
    echo "AUTOMATED TEST RUN FAILED"
fi

exit $integration_test_status
