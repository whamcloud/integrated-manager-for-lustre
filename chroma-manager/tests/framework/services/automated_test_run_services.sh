#!/bin/sh

set -ex

[ -r localenv ] && . localenv

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
yum clean metadata
yum install -y git python-virtualenv python-setuptools python-devel gcc make graphviz-devel rabbitmq-server postgresql-server postgresql-devel rabbitmq-server mod_wsgi mod_ssl telnet python-ethtool

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
# TODO: sleeping is racy.  should check for up-ness, not just assume it
#       will happen within 5 seconds
sleep 5  # Unfortunately postgresql start seems to return before its truly up and ready for business
su postgres -c 'createuser -R -S -d chroma'
su postgres -c 'createdb -O chroma chroma'
sed -i -e '/local[[:space:]]\+all/i\
local   all         chroma                            trust' /var/lib/pgsql/data/pg_hba.conf
service postgresql restart
EOF

virtualenv --relocatable .
tar -czf ../chroma_test_env.tgz .
scp ../chroma_test_env.tgz chromatest@$CHROMA_MANAGER:~

ssh chromatest@$CHROMA_MANAGER <<EOF
set -ex
mkdir -p chroma_test_env
cd chroma_test_env
tar -xzf ~/chroma_test_env.tgz
virtualenv --no-site-packages .
source bin/activate
cd chroma/chroma-manager/

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
cd $CHROMA_DIR/../..
mkdir -p test_reports
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
