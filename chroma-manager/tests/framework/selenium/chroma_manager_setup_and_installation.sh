#!/bin/bash -ex

[ -r localenv ] && . localenv

ARCHIVE_NAME=ieel-2.0.1.tar.gz
CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}
CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$CHROMA_DIR/chroma-manager/tests/framework/selenium/cluster_config.json"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

MEASURE_COVERAGE=${MEASURE_COVERAGE:-false}
GOOGLE_REPO=${GOOGLE_REPO:-"http://cobbler/cobbler/repo_mirror/google_chrome-stable-x86_64"}  # If not on Toro, can pass in http://dl.google.com/linux/chrome/rpm/stable/x86_64

echo "Beginning installation and setup on $CHROMA_MANAGER..."

ssh root@$TEST_RUNNER <<EOF
set -ex
yum install --setopt=retries=50 --setopt=timeout=180 -y unzip tar bzip2 python-virtualenv python-devel gcc make tigervnc-server npm git firefox java-1.7.0-openjdk haveged
yum update --setopt=retries=50 --setopt=timeout=180 -y nss

# Selenium server needs entropy
service haveged start

if [ ! -z "$GOOGLE_REPO" ]; then
  # Install Google Chrome
  cat << EOC >> /etc/yum.repos.d/google.repo
[google]
name=Google
baseurl=$GOOGLE_REPO
enabled=0
gpgcheck=0
retries=50
timeout=180
EOC
  yum --enablerepo=google install -y google-chrome-stable
fi

# Create a user so we can run the tests as non-root
useradd chromatest
su chromatest <<EOC
mkdir -p ~/.ssh
touch ~/.ssh/authorized_keys
EOC
cat .ssh/id_rsa.pub >> /home/chromatest/.ssh/authorized_keys
cp .ssh/* ~chromatest/.ssh/
chown chromatest.chromatest ~chromatest/.ssh/*
chmod 600 ~chromatest/.ssh/*
EOF

tar -czf ../chroma.tgz ./chroma/
scp ../chroma.tgz chromatest@$TEST_RUNNER:~
tar -czf ../pip_cache.tgz ../pip_cache/
scp ../pip_cache.tgz chromatest@$TEST_RUNNER:~

ssh chromatest@$TEST_RUNNER <<"EOF"
set -ex

mkdir $HOME/bin

# Install Chromedriver
LATEST_CHROMEDRIVER_RELEASE=$(curl -f http://chromedriver.storage.googleapis.com/LATEST_RELEASE)
wget http://chromedriver.storage.googleapis.com/$LATEST_CHROMEDRIVER_RELEASE/chromedriver_linux64.zip
unzip chromedriver_linux64.zip -d $HOME/bin/

# Download Selenium jar
wget -O $HOME/bin/selenium-server-standalone.jar https://selenium-release.storage.googleapis.com/2.40/selenium-server-standalone-2.40.0.jar

# Set up the virtualenv to run the tests in
tar -xzf ~/pip_cache.tgz
mkdir chroma_test_env
cd chroma_test_env
virtualenv --no-site-packages .
source bin/activate
tar -xzf ~/chroma.tgz
cd chroma/chroma-manager

# Install pip-based requirements
make requirements

# Remove requirements not compatible with python 2.7,
# not needed for running the tests anyways
for package in importlib greenlet gevent psycopg2 pygraphviz; do
  sed -i "s/^.*$package.*$//g" requirements.txt
done

# Install the remaining pip requirements
python tests/utils/pip_install_requirements.py ~/pip_cache

# Install npm-based requirements
cd chroma_ui
npm install
cd ../chroma_ui_new
npm install
cd ../realtime
npm install

# Configure VNC server
cd ~
vncpasswd <<EOC
somepassword
somepassword
EOC
EOF

# Install and setup chroma manager
scp ../$ARCHIVE_NAME $CHROMA_DIR/chroma-manager/tests/utils/install.exp root@$CHROMA_MANAGER:/tmp
ssh root@$CHROMA_MANAGER "#don't do this, it hangs the ssh up, when used with expect, for some reason: exec 2>&1
set -ex
cat << \"EOF\" >> /etc/yum.repos.d/autotest.repo
retries=50
timeout=180
EOF
yum install -y python-mock expect
if $MEASURE_COVERAGE; then
    yum install -y python-coverage
fi
rm -f /etc/yum.repos.d/autotest.repo
yum clean metadata
# Install from the installation package
cd /tmp
tar xzvf $ARCHIVE_NAME
cd $(basename $ARCHIVE_NAME .tar.gz)
if ! expect ../install.exp $CHROMA_USER $CHROMA_EMAIL $CHROMA_PASS ${CHROMA_NTP_SERVER:-localhost}; then
    rc=${PIPESTATUS[0]}
    cat /var/log/chroma/install.log
    exit $rc
fi

cat <<\"EOF1\" > /usr/share/chroma-manager/local_settings.py
import logging
LOG_LEVEL = logging.DEBUG
EOF1

mkdir -p /usr/share/chroma-manager/tests/framework/selenium/"

scp -r chroma/chroma-manager/tests/framework/selenium/mock_agent root@$CHROMA_MANAGER:/usr/share/chroma-manager/tests/framework/selenium/mock_agent
scp -r chroma/chroma-manager/tests/unit/ root@$CHROMA_MANAGER:/usr/share/chroma-manager/tests/unit
scp chroma/chroma-manager/tests/__init__.py root@$CHROMA_MANAGER:/usr/share/chroma-manager/tests/__init__.py

# copy the .py's that where stripped (HYD-1849)
scp chroma/chroma-manager/chroma_core/services/job_scheduler/agent_rpc.py root@$CHROMA_MANAGER:/usr/share/chroma-manager/chroma_core/services/job_scheduler/agent_rpc.py
scp chroma/chroma-manager/chroma_core/services/plugin_runner/agent_daemon.py root@$CHROMA_MANAGER:/usr/share/chroma-manager/chroma_core/services/plugin_runner/agent_daemon.py

ssh root@$CHROMA_MANAGER "exec 2>&1; set -ex
# patch the agent
cat /usr/share/chroma-manager/tests/framework/selenium/mock_agent/agent_rpc_addon.py >> /usr/share/chroma-manager/chroma_core/services/job_scheduler/agent_rpc.py

# patch the plugin manager
cat /usr/share/chroma-manager/tests/framework/selenium/mock_agent/agent_daemon_addon.py >> /usr/share/chroma-manager/chroma_core/services/plugin_runner/agent_daemon.py

if $MEASURE_COVERAGE; then
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
fi

chroma-config restart
"

echo "End installation and setup."
