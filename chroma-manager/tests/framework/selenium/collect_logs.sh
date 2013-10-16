#!/bin/bash
set +e
set -x

[ -r localenv ] && . localenv

CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}
CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$CHROMA_DIR/chroma-manager/tests/framework/selenium/cluster_config.json"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

MEASURE_COVERAGE=${MEASURE_COVERAGE:-false}

ssh root@$CHROMA_MANAGER "tar -czf - -C /var/log/chroma . -C /var/log/httpd . -C /var/log messages" | tar -xzf - -C $WORKSPACE/test_logs
scp chromatest@$TEST_RUNNER:.vnc/*.log $WORKSPACE/test_logs/
scp chromatest@$TEST_RUNNER:chroma_test_env/chroma/chroma-manager/*log $WORKSPACE/test_logs/
scp -r chromatest@$TEST_RUNNER:chroma_test_env/chroma/chroma-manager/failed-screen-shots/ $WORKSPACE
scp -r chromatest@$TEST_RUNNER:chroma_test_env/chroma/chroma-manager/failed-browser-logs/ $WORKSPACE

if $MEASURE_COVERAGE; then
  ssh root@$CHROMA_MANAGER <<EOF
    chroma-config stop
    cd /var/tmp/
    coverage combine
EOF
  scp root@$CHROMA_MANAGER:/var/tmp/.coverage $WORKSPACE/.coverage.raw
fi

exit 0
