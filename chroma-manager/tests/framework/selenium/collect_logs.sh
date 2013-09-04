set +e

[ -r localenv ] && . localenv

CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}
CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$CHROMA_DIR/chroma-manager/tests/framework/selenium/cluster_config.json"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

MEASURE_COVERAGE=${MEASURE_COVERAGE:-false}

scp root@$CHROMA_MANAGER:/var/log/chroma/*.log $WORKSPACE/test_logs/
scp root@$CHROMA_MANAGER:/var/log/messages $WORKSPACE/test_logs/
if $MEASURE_COVERAGE; then
  ssh root@$CHROMA_MANAGER <<EOF
    chroma-config stop
    cd /var/tmp/
    coverage combine
EOF
  scp root@$CHROMA_MANAGER:/var/tmp/.coverage $WORKSPACE/.coverage.raw
fi
exit 0
