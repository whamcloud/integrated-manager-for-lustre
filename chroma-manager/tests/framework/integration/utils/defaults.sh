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

PROVISIONER=${PROVISIONER:-"$HOME/provisionchroma -v -S --provisioner /home/bmurrell/provisioner"}


MEASURE_COVERAGE=${MEASURE_COVERAGE:-false}

# Variables that we expect to be set upstream, no "default"
set +x  # DONT REMOVE/COMMENT or you will risk exposing the jenkins-pull api token in the console logs.
export JENKINS_USER=${JENKINS_USER:-jenkins-pull}
export JENKINS_PULL=${JENKINS_PULL:?"Need to set JENKINS_PULL"}
set -x
BUILD_JOB_NAME=${BUILD_JOB_NAME:?"Need to set BUILD_JOB_NAME"}
BUILD_JOB_BUILD_NUMBER=${BUILD_JOB_BUILD_NUMBER:?"Need to set BUILD_JOB_BUILD_NUMBER"}
JOB_URL=${JOB_URL:?"Need to set JOB_URL"}
WORKSPACE=${WORKSPACE:?"Need to set WORKSPACE"}
TEST_DISTRIBUTION=${TEST_DISTRIBUTION:-"el6.6"}
