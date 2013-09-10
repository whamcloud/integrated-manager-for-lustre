#!/bin/bash
set -x

[ -r localenv ] && . localenv

CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}
CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$CHROMA_DIR/chroma-manager/tests/framework/selenium/cluster_config.json"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

trap "set +e; scp -r chromatest@$TEST_RUNNER:test_reports $WORKSPACE" EXIT

scp $CLUSTER_CONFIG chromatest@$TEST_RUNNER:cluster_config.json
ssh chromatest@$TEST_RUNNER <<"EOF"
set -x
mkdir test_reports
source chroma_test_env/bin/activate
cd chroma_test_env/chroma/chroma-manager
vncserver :1
export DISPLAY=$(hostname):1
for FILE in $(cd tests/selenium && ls test_*.py); do
  CLUSTER_DATA=tests/selenium/test_data.json PATH=$PATH:$HOME/chroma_test_env nosetests --verbosity=2 --with-xunit --xunit-file=$HOME/test_reports/selenium-test-results_$FILE.xml --tc-format=json --tc-file=$HOME/cluster_config.json tests/selenium/$FILE || true
  killall chromedriver
done
EOF

exit 0
