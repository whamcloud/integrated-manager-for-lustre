#!/bin/sh

set -ex

[ -r localenv ] && . localenv

# Remove test results and coverage reports from previous run
rm -rfv $PWD/test_reports/*
mkdir -p $PWD/test_reports

CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}
CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$CHROMA_DIR/chroma-manager/tests/framework/services/cluster_config.json"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

MEASURE_COVERAGE=${MEASURE_COVERAGE:-false}
TESTS=${TESTS:-"tests/services/"}

echo "Beginning installation and setup..."

# Install and setup chroma manager
ssh root@$CHROMA_MANAGER <<EOF
set -ex
# Install non-python/pipable dependencies
cat <<EOC > /etc/yum.repos.d/internal_epel.repo
[addon-epel6-x86_64]
name=addon-epel6-x86_64
baseurl=http://10.10.0.6/cobbler/repo_mirror/addon-epel6-x86_64
enabled=1
gpgcheck=0
priority=99
EOC
yum clean metadata
yum install -y git python-pip python-virtualenv python-setuptools python-devel gcc make graphviz-devel rabbitmq-server postgresql-server postgresql-devel rabbitmq-server mod_wsgi mod_ssl telnet python-ethtool

# Create a user so we can run chroma as non-root
useradd chromatest
su chromatest
mkdir -p ~/.ssh
touch ~/.ssh/authorized_keys
exit
cat .ssh/id_rsa.pub >> /home/chromatest/.ssh/authorized_keys
scp .ssh/* chromatest@$CHROMA_MANAGER:.ssh/

# Configure rabbitmq
chkconfig rabbitmq-server on

# Some witch-craft to run rabbitmq as non-root in linux
echo "%rabbitmq ALL=(ALL) NOPASSWD: /usr/sbin/rabbitmqctl"  > /etc/sudoers.d/rabbitmqctl
chmod 440 /etc/sudoers.d/rabbitmqctl
sed -i "s/Defaults    requiretty/# Defaults    requiretty/g" /etc/sudoers
sed -i "s/rabbitmq:x:\([0-9]*\):[a-z]*/rabbitmq:x:\1:chromatest/g" /etc/group
# End witchcraft

service rabbitmq-server start &> rabbitmq_startup.log
cat rabbitmq_startup.log

# Configure postgres
chkconfig postgresql on
service postgresql initdb
service postgresql start
sleep 5  # Unfortunately postgresql start seems to return before its truly up and ready for business
su postgres -c 'createuser -R -S -d chroma'
su postgres -c 'createdb -O chroma chroma'
sed -i -e '/local[[:space:]]\+all/i\
local   all         chroma                            trust' /var/lib/pgsql/data/pg_hba.conf
service postgresql restart
EOF

tar -czf chroma.tgz chroma
scp chroma.tgz chromatest@$CHROMA_MANAGER:~

ssh chromatest@$CHROMA_MANAGER <<EOF
set -ex
mkdir -p chroma_test_env
virtualenv --no-site-packages chroma_test_env
cd chroma_test_env
source bin/activate
tar -xzf ~/chroma.tgz

cd ~/chroma_test_env/chroma/chroma-manager
if [ ! -f requirements.txt ]; then
  make requirements
fi
pip install -r requirements.txt

unset http_proxy
unset https_proxy

if $MEASURE_COVERAGE; then
  cat <<EOC > /home/chromatest/chroma_test_env/chroma/chroma-manager/.coveragerc
[run]
data_file = /var/tmp/.coverage
parallel = True
source = /home/chromatest/chroma_test_env/chroma
EOC
  cat <<EOC  > /home/chromatest/chroma_test_env/lib/python2.6/site-packages/sitecustomize.py
import coverage
cov = coverage.coverage(config_file='/home/chromatest/chroma_test_env/chroma/chroma-manager/.coveragerc', auto_data=True)
cov.start()
cov._warn_no_data = False
cov._warn_unimported_source = False
EOC
fi

cd ~/chroma_test_env/chroma/chroma-manager

# Enable DEBUG logging
cat <<"EOF1" > local_settings.py
import logging
LOG_LEVEL = logging.DEBUG
EOF1

python manage.py dev_setup --no-bundles

set +e
echo "Begin running tests..."
PYTHONPATH=. nosetests --verbosity=2 --with-xunit --xunit-file /home/chromatest/test_report.xml $TESTS
ls /home/chromatest/

EOF
test_status=$?

echo "End running tests."

set +e
scp chromatest@$CHROMA_MANAGER:test_report.xml ./test_reports/
mkdir -p test_logs
scp chromatest@$CHROMA_MANAGER:chroma_test_env/chroma/chroma-manager/*.log ./test_logs/
scp root@$CHROMA_MANAGER:/var/log/messages ./test_logs/
if $MEASURE_COVERAGE; then
  mkdir -p coverage_reports
  ssh chromatest@$CHROMA_MANAGER <<EOF
    set -x
    source chroma_test_env/bin/activate
    cd /var/tmp/
    coverage combine
EOF
  scp chromatest@$CHROMA_MANAGER:/var/tmp/.coverage ./.coverage.raw
fi
set -e

if [ $test_status -ne 0 ]; then
    echo "AUTOMATED TEST RUN FAILED"
fi

exit $test_status
