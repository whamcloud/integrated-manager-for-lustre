#!/bin/bash -xe

# allow caller to override MAPPED_DIR, but default if they don't
MAPPED_DIR="${MAPPED_DIR:-/build}"

echo 'travis_fold:start:yum'
yum -y install git mock rpm-build ed sudo make rpmdevtools rpmlint
echo 'travis_fold:end:yum'

# edit per the module if specified
if [ -f mock-default.cfg.ed ]; then
    cp /etc/mock/default.cfg{,.orig}
    ed /etc/mock/default.cfg < mock-default.cfg.ed
    diff -u /etc/mock/default.cfg{.orig,} || true
fi

# add our repos to the mock configuration
ed <<"EOF" /etc/mock/default.cfg
$i

[copr-be.cloud.fedoraproject.org_results_managerforlustre_manager-for-lustre_epel-7-x86_64_]
name=added from: https://copr-be.cloud.fedoraproject.org/results/managerforlustre/manager-for-lustre/epel-7-x86_64/
baseurl=https://copr-be.cloud.fedoraproject.org/results/managerforlustre/manager-for-lustre/epel-7-x86_64/
enabled=1
.
wq
EOF

eval export "$(grep -e "^TRAVIS=" -e "^TRAVIS_EVENT_TYPE=" "$MAPPED_DIR"/travis_env)"

if [ "$TRAVIS_EVENT_TYPE" = "push" ]; then
    eval export "$(grep -e "^TRAVIS_BRANCH=" "$MAPPED_DIR"/travis_env)"
    TEST_BRANCH="$TRAVIS_BRANCH"
elif [ "$TRAVIS_EVENT_TYPE" = "pull_request" ]; then
    eval export "$(grep -e "^TRAVIS_PULL_REQUEST_BRANCH=" \
                        "$MAPPED_DIR"/travis_env)"
    TEST_BRANCH="$TRAVIS_PULL_REQUEST_BRANCH"
else
    echo "Don't know how to handle TRAVIS_EVENT_TYPE $TRAVIS_EVENT_TYPE."
    exit 1
fi

groupadd --gid "$(stat -c '%g' "$MAPPED_DIR")" mocker
useradd --uid "$(stat -c '%u' "$MAPPED_DIR")" --gid "$(stat -c '%g' "$MAPPED_DIR")" mocker
usermod -a -G mock mocker

pushd "$MAPPED_DIR"
make install_build_deps
popd

if ! su - mocker <<EOF; then
set -xe
cd "$MAPPED_DIR"
make rpmlint
make DIST_VERSION="$TEST_BRANCH" build_test
for rpm in \$(ls /var/lib/mock/epel-7-x86_64/result/*.rpm); do
    echo "------- \$rpm -------"
    rpm -qlp \$rpm
done
EOF
    exit "${PIPESTATUS[0]}"
fi

exit 0
