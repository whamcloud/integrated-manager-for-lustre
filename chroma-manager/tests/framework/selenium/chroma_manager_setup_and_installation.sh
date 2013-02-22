set -x

CHROMA_MANAGER=${CHROMA_MANAGER:='hydra-2-selenium-chroma-manager-1'}

echo "Beginning installation and setup on $CHROMA_MANAGER..."

# Remove old files from previous run
ssh $CHROMA_MANAGER "rm -rvf ~/mock_agent/*"
ssh $CHROMA_MANAGER "rm -rvf ~/requirements.txt"
ssh $CHROMA_MANAGER "rm -rvf ~/rpms/*"
ssh $CHROMA_MANAGER "mkdir -p ~/rpms/"

# Copy rpms to each of the machines
scp $(ls ~/selenium/rpms/arch\=x86_64\,distro\=el6/dist/chroma-manager-*| grep -v integration-tests) $CHROMA_MANAGER:~/rpms/
scp ~/selenium/requirements.txt $CHROMA_MANAGER:~
scp -r ~/selenium/mock_agent $CHROMA_MANAGER:~

# Install and setup chroma manager
ssh $CHROMA_MANAGER <<"EOF"
set -x

chroma-config stop
logrotate -fv /etc/logrotate.d/chroma-manager

yum remove -y chroma-manager*
rm -rf /usr/share/chroma-manager/
rm -f /usr/bin/chroma*
echo "drop database chroma; create database chroma;" | mysql -u root

source ~/.bash_profile
pip install --force-reinstall -r requirements.txt <<EOC
s

EOC
yum install -y ~/rpms/chroma-manager-*

echo "import logging
LOG_LEVEL = logging.DEBUG" > /usr/share/chroma-manager/local_settings.py
cat ~/mock_agent/agent_rpc_addon.py >> /usr/share/chroma-manager/chroma_core/services/job_scheduler/agent_rpc.py
cp -r ~/mock_agent/tests/ /usr/share/chroma-manager/tests/
cp ~/mock_agent/*.json /usr/share/chroma-manager/

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
cov._warn_no_data = False
cov._warn_unimported_source = False
" > /usr/lib/python2.6/site-packages/sitecustomize.py

chroma-config setup debug chr0m4_d3bug localhost > /root/chroma_config.log 2>&1
cat /root/chroma_config.log
rm -f /root/chroma_config.log
EOF

echo "End installation and setup."
