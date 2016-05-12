# Function returns creates fake passfile in the directory provided.
fake_test_pass() {
    local report_file="$1"
    local result_location="$2"
    local build_number="$3"

    mkdir -p ${result_location}

    cat <<EOF > ${result_location}/${report_file}_${build_number}.xml
<testsuite name="nosetests" tests="1" errors="0" failures="0" skip="0">
<testcase classname="no.actual.test" name="no_test_${build_number}_$(date +%s)" time="0.000"/>
</testsuite>
EOF

}