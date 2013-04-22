set -ex

[ -r localenv ] && . localenv

CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}
CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$CHROMA_DIR/chroma-manager/tests/framework/selenium/cluster_config.json"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

MEASURE_COVERAGE=${MEASURE_COVERAGE:-false}

echo "Beginning installation and setup on $CHROMA_MANAGER..."


# Install and setup chroma manager
ssh root@$CHROMA_MANAGER <<EOF
set -ex
yum install -y chroma-manager python-mock

cat <<"EOF1" > /usr/share/chroma-manager/local_settings.py
import logging
LOG_LEVEL = logging.DEBUG
EOF1

mkdir -p /usr/share/chroma-manager/tests/framework/selenium/
EOF

scp -r chroma/chroma-manager/tests/framework/selenium/mock_agent root@$CHROMA_MANAGER:/usr/share/chroma-manager/tests/framework/selenium/mock_agent
scp -r chroma/chroma-manager/tests/unit/ root@$CHROMA_MANAGER:/usr/share/chroma-manager/tests/unit
scp chroma/chroma-manager/tests/__init__.py root@$CHROMA_MANAGER:/usr/share/chroma-manager/tests/__init__.py

ssh root@$CHROMA_MANAGER <<EOF
cat /usr/share/chroma-manager/tests/framework/selenium/mock_agent/agent_rpc_addon.py >> /usr/share/chroma-manager/chroma_core/services/job_scheduler/agent_rpc.py

if $MEASURE_COVERAGE; then
  yum install -y python-coverage
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
fi

chroma-config setup debug chr0m4_d3bug localhost &> /root/chroma_config.log
cat /root/chroma_config.log
rm -f /root/chroma_config.log
EOF

echo "End installation and setup."
