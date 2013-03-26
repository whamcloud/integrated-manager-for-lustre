#!/bin/sh

set -ex

[ -r localenv ] && . localenv

# Remove test results and coverage reports from previous run
rm -rfv $PWD/test_reports/*
mkdir -p $PWD/test_reports

CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}
CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$CHROMA_DIR/chroma-manager/tests/simulator.json"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

MEASURE_COVERAGE=${MEASURE_COVERAGE:-false}
TESTS=${TESTS:-"tests/integration/shared_storage_configuration/"}

echo "Beginning installation and setup..."

# Install and setup chroma manager
ssh root@$CHROMA_MANAGER <<EOF
set -ex
# Install non-python/pipable dependencies

# TEMPORARY until we get caught up with CentOS 6.4
cat <<EOC > /etc/yum.repos.d/internal_epel.repo
[addon-epel6-x86_64]
name=addon-epel6-x86_64
baseurl=http://10.10.0.6/cobbler/repo_mirror/addon-epel6-x86_64
enabled=1
gpgcheck=0
EOC
yum install -y rabbitmq-server
rm -f /etc/yum.repos.d/internal_epel.repo
#END TEMPORARY

wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
yum install -y epel-release-6-8.noarch.rpm
yum install -y git python-pip python-virtualenv python-setuptools python-devel gcc make graphviz-devel rabbitmq-server postgresql-server postgresql-devel mod_wsgi mod_ssl
ln -s /usr/bin/pip-python /usr/bin/pip

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
cat <<EOC > /usr/local/bin/rabbitmqctl
#!/bin/sh
if [ \\\`id -u\\\` != 0 ]; then
  sudo /usr/sbin/rabbitmqctl "\\\$@"
else
  /usr/sbin/rabbitmqctl "\\\$@"
fi
EOC
chmod a+rx /usr/local/bin/rabbitmqctl
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

cd ~/chroma_test_env/chroma/chroma-agent/
make version
python setup.py develop

cd ~/chroma_test_env/chroma/cluster-sim/
python setup.py develop

cd ~/chroma_test_env/chroma/chroma-manager
python manage.py dev_setup
python manage.py supervisor  &> /dev/null &
supervisor_pid=\$!
sleep 30  # Give a chance for the services to start - TODO: Add a check to setUp in tests themselves if the services are ready.

set +e
echo "Begin running tests..."
if $MEASURE_COVERAGE; then
  NOSE_COVERAGE_ARGS="--with-coverage"
else
  NOSE_COVERAGE_ARGS=""
fi
nosetests --verbosity=2 --tc-file=tests/simulator.json --tc-format=json --with-xunit --xunit-file /home/chromatest/test_report.xml \$NOSE_COVERAGE_ARGS $TESTS

kill \$supervisor_pid
EOF
integration_test_status=$?

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

if [ $integration_test_status -ne 0 ]; then
    echo "AUTOMATED TEST RUN FAILED"
fi

exit $integration_test_status
