#!/bin/bash
set +e
set -x

[ -r localenv ] && . localenv

CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}
CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$CHROMA_DIR/chroma-manager/tests/framework/gui/cluster_config.json"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

MEASURE_COVERAGE=${MEASURE_COVERAGE:-false}

scp chromatest@$TEST_RUNNER:.vnc/*.log $WORKSPACE/test_logs/
scp -r chromatest@$TEST_RUNNER:chroma_test_env/chroma/chroma-manager/chroma_ui_new/*.log $WORKSPACE/test_logs/

exit 0
