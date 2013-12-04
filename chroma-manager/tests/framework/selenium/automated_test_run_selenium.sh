#!/bin/bash
set -x

[ -r localenv ] && . localenv

CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}
CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$CHROMA_DIR/chroma-manager/tests/framework/selenium/cluster_config.json"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

trap "set +e; scp -r chromatest@$TEST_RUNNER:test_reports $WORKSPACE" EXIT

scp $CLUSTER_CONFIG chromatest@$TEST_RUNNER:cluster_config.json
ssh chromatest@$TEST_RUNNER <<"EOF"
set -ex
mkdir test_reports
source chroma_test_env/bin/activate
vncserver :1
export DISPLAY=$(hostname):1

# Run Karma GUI unit tests
cd $HOME/chroma_test_env/chroma/chroma-manager/chroma_ui
./node_modules/karma/bin/karma start --browsers Chrome,Firefox --singleRun true --reporters dots,junit || true
mv test-results.xml $HOME/test_reports/karma-test-results.xml

# Run Selenium GUI Tests
cd $HOME/chroma_test_env/chroma/chroma-manager
CLUSTER_DATA=tests/selenium/test_data.json PATH=$PATH:$HOME/chroma_test_env nosetests --verbosity=2 --with-xunit --xunit-file=$HOME/test_reports/selenium-test-results.xml --tc-format=json --tc-file=$HOME/cluster_config.json tests/selenium/ || true
EOF

exit 0
