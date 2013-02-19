set +e

for file in `ls tests/selenium/test_*.py | xargs -n1 basename`; do
  CLUSTER_DATA=tests/selenium/test_data.json PATH=$PATH:. nosetests --verbosity=2 --with-xunit --xunit-file=$WORKSPACE/test_reports/selenium-test-results_$file.xml tests/selenium/$file --tc-format=json --tc-file=tests/framework/selenium/cluster_config.json
  ps aux | grep -e 'chromedriver' | grep -v grep | grep jenkins | awk '{print $2}' | xargs -i kill {}
done

echo "Test cleanup..."
set +e
rm -rvf /tmp/.com.google.Chrome.*
exit 0
