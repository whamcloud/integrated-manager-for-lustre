set -ex

[ -r localenv ] && . localenv

CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}
CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$CHROMA_DIR/chroma-manager/tests/framework/selenium/cluster_config.json"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

MEASURE_COVERAGE=${MEASURE_COVERAGE:-false}

echo "Beginning installation and setup on $CHROMA_MANAGER..."


# Install and setup chroma manager
scp ../chroma.tar.gz root@$CHROMA_MANAGER:/tmp
ssh root@$CHROMA_MANAGER "exec 2>&1; set -ex
yum install -y python-mock
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

mkdir -p /usr/share/chroma-manager/tests/framework/selenium/"

scp -r chroma/chroma-manager/tests/framework/selenium/mock_agent root@$CHROMA_MANAGER:/usr/share/chroma-manager/tests/framework/selenium/mock_agent
scp -r chroma/chroma-manager/tests/unit/ root@$CHROMA_MANAGER:/usr/share/chroma-manager/tests/unit
scp chroma/chroma-manager/tests/__init__.py root@$CHROMA_MANAGER:/usr/share/chroma-manager/tests/__init__.py

ssh root@$CHROMA_MANAGER "exec 2>&1; set -ex
cat /usr/share/chroma-manager/tests/framework/selenium/mock_agent/agent_rpc_addon.py >> /usr/share/chroma-manager/chroma_core/services/job_scheduler/agent_rpc.py

if $MEASURE_COVERAGE; then
  yum install -y python-coverage
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
fi"

echo "End installation and setup."
