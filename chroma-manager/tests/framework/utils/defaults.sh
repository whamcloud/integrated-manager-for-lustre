# auth.sh contains the JENKINS_PULL environmental variable so we can avoid
# printing it into the console in plaintext calling this script.
set +x  # DONT REMOVE/COMMENT or you will risk exposing the jenkins-pull api token in the console logs.
. $HOME/auth.sh
set -x

[ -r localenv ] && . localenv

spacelist_to_commalist() {
    echo $@ | tr ' ' ','
}

d=${0%/*}
if [[ $d != /* ]]; then
    d=${PWD}/$d
fi
while [ ! -f $d/include/Makefile.version ]; do
    d=${d%/*}
done
export IEEL_VERSION=$(make -f $d/include/Makefile.version .ieel_version)

export PROVISIONER=${PROVISIONER:-"$HOME/provisionchroma -v -S --provisioner /home/bmurrell/provisioner"}

if [ "$MEASURE_COVERAGE" != "true" -a "$MEASURE_COVERAGE" != "false" ]; then
    {
        echo "Whoa!  We hit TEI-3576."
        echo
        env
        echo
        echo "At test run start, env was:"
        cat /tmp/env-"$JOB_NAME"-"$BUILD_NUMBER"
    } | mail -s "TEI-3576" brian.murrell@intel.com

    # now set it to a sane value
    MEASURE_COVERAGE="false"
fi
rm -f /tmp/env-"$JOB_NAME"-"$BUILD_NUMBER"

# Variables that we expect to be set upstream, no "default"
set +x  # DONT REMOVE/COMMENT or you will risk exposing the jenkins-pull api token in the console logs.
export JENKINS_USER=${JENKINS_USER:-jenkins-pull}
export JENKINS_PULL=${JENKINS_PULL:?"Need to set JENKINS_PULL"}
set -x
export BUILD_JOB_NAME=${BUILD_JOB_NAME:?"Need to set BUILD_JOB_NAME"}
export BUILD_JOB_BUILD_NUMBER=${BUILD_JOB_BUILD_NUMBER:?"Need to set BUILD_JOB_BUILD_NUMBER"}
export JOB_URL=${JOB_URL:?"Need to set JOB_URL"}
export WORKSPACE=${WORKSPACE:?"Need to set WORKSPACE"}
export TEST_DISTRIBUTION=${TEST_DISTRIBUTION:-"el6.6"}
export CLUSTER_CONFIG="cluster_cfg.json"
