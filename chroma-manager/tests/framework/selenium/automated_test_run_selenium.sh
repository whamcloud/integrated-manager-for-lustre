set +e

[ -r localenv ] && . localenv

CHROMA_DIR=${CHROMA_DIR:-"$PWD/chroma/"}
CLUSTER_CONFIG=${CLUSTER_CONFIG:-"$CHROMA_DIR/chroma-manager/tests/framework/selenium/cluster_config.json"}

eval $(python $CHROMA_DIR/chroma-manager/tests/utils/json_cfg2sh.py "$CLUSTER_CONFIG")

for file in $(ls $CHROMA_DIR/chroma-manager/tests/selenium/test_*.py | xargs -n1 basename | sort); do
  CLUSTER_DATA=$CHROMA_DIR/chroma-manager/tests/selenium/test_data.json PATH=$PATH:. nosetests --verbosity=2 --with-xunit --xunit-file=$WORKSPACE/test_reports/selenium-test-results_$file.xml $CHROMA_DIR/chroma-manager/tests/selenium/$file --tc-format=json --tc-file=$CLUSTER_CONFIG
  ps aux | grep -e 'chromedriver' | grep -v grep | grep jenkins | awk '{print $2}' | xargs -i kill {}
done

echo "Test cleanup..."
set +e
rm -rvf /tmp/.com.google.Chrome.*
exit 0
