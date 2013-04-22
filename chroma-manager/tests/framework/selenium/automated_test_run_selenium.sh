set +e

[ -r localenv ] && . localenv

CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}
CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$CHROMA_DIR/chroma-manager/tests/framework/selenium/cluster_config.json"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

MEASURE_COVERAGE=${MEASURE_COVERAGE:-false}

for file in $(ls $CHROMA_DIR/chroma-manager/tests/selenium/test_*.py | xargs -n1 basename | sort); do
  CLUSTER_DATA=$CHROMA_DIR/chroma-manager/tests/selenium/test_data.json PATH=$PATH:. nosetests --verbosity=2 --with-xunit --xunit-file=$WORKSPACE/test_reports/selenium-test-results_$file.xml $CHROMA_DIR/chroma-manager/tests/selenium/$file --tc-format=json --tc-file=$CLUSTER_CONFIG
  ps aux | grep -e 'chromedriver' | grep -v grep | grep jenkins | awk '{print $2}' | xargs -i kill {}
done

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

echo "Test cleanup..."
set +e
rm -rvf /tmp/.com.google.Chrome.*
exit 0
