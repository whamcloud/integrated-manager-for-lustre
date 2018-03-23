# This file will selectively autopass some commits.

# At present bumps to the GUI only are auto passed.

# shellcheck disable=SC1091
. chroma-manager/tests/framework/utils/gui_update.sh
# shellcheck disable=SC1091
. chroma-manager/tests/framework/utils/fake_pass.sh

check_for_autopass() {
    # currently defined tests:
    # integration-tests-existing-filesystem-configuration
    # integration-tests-shared-storage-configuration
    # test-services
    # upgrade-tests
    # unit-tests
    # vvvvvvvvvvv this should come from a pragma in the commit message
    local all_tests="integration-tests-existing-filesystem-configuration
                     integration-tests-shared-storage-configuration
                     test-services
                     unit-tests
                     upgrade-tests"
    local commit_message tests_to_run
    commit_message=$(git log -n 1)
    tests_to_run=$(echo "$commit_message" | sed -ne '/^ *Run-tests:/s/^ *Run-tests: *//p')
    if [ -n "$tests_to_run" ]; then
        tests_to_skip=$all_tests
        for t in $tests_to_run; do
            tests_to_skip=${tests_to_skip/$t/}
        done
    else
        tests_to_skip=$(echo "$commit_message" | sed -ne '/^ *Skip-tests:/s/^ *Skip-tests: *//p')
    fi
    # set any environment the test run wants
    local environment
    environment=$(echo "$commit_message" | sed -ne '/^ *Environment:/s/^ *Environment: *//p')
    if [ -n "$environment" ]; then
        # shellcheck disable=SC2163
        # shellcheck disable=SC2086
        export ${environment?}
    fi

    local t
    for t in $tests_to_skip; do
        if [[ $JOB_NAME == "$t" || $JOB_NAME == "$t/*" ]]; then
            echo "skipping this test due to {Run|Skip}-tests pragma"
            fake_test_pass "tests_skipped_because_commit_pragma" "$WORKSPACE/test_reports/" "$BUILD_NUMBER"
            exit 1
        fi
    done

    tests_required_for_gui_bumps="chroma-tests-services"

    if [[ $BUILD_JOB_NAME = "*-reviews" ]] && gui_bump && [[ ! $tests_required_for_gui_bumps = "$JOB_NAME" ]]; then
      fake_test_pass "tests_skipped_because_gui_version_bump" "$WORKSPACE/test_reports/" "$BUILD_NUMBER"
      exit 0
    fi

    # regex matches separated by |
    supported_distro_versions="7\.[0-9]+"
    if [[ ! $TEST_DISTRO_VERSION =~ $supported_distro_versions ]] && ([ -z "$UPGRADE_TEST_DISTRO" ] || [[ ! $UPGRADE_TEST_DISTRO =~ $supported_distro_versions ]]); then
      fake_test_pass "tests_skipped_because_unsupported_distro_$TEST_DISTRO_VERSION" "$WORKSPACE/test_reports/" "$BUILD_NUMBER"
      exit 0
    fi

    # RHEL 7.5 won't upgrade CentOS 7.3
    # still true?
    #if [[ ($JOB_NAME == upgrade-tests || $JOB_NAME == upgrade-tests/*) &&
    #      ("$TEST_DISTRO_VERSION" = "7.3" && "$UPGRADE_DISTRO_VERSION" = "7.5") &&
    #       $TEST_DISTRO_NAME != rhel ]]; then
    #    fake_test_pass "upgrade-tests_skipped_on_centos7.3" "$WORKSPACE/test_reports/" "${BUILD_NUMBER}"
    #    exit 0
    #fi

}  # end of check_for_autopass()
