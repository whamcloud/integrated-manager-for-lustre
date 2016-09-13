# This file will selectively autopass some commits.

# At present bumps to the GUI only are auto passed.

. chroma-manager/tests/framework/utils/gui_update.sh
. chroma-manager/tests/framework/utils/fake_pass.sh

check_for_autopass() {
    tests_required_for_gui_bumps="chroma-tests-services"

    if [[ $BUILD_JOB_NAME = *-reviews ]] && gui_bump && [[ ! $tests_required_for_gui_bumps = $JOB_NAME ]]; then
      fake_test_pass "tests_skipped_because_gui_version_bump" "$WORKSPACE/test_reports/" ${BUILD_NUMBER}
      exit 0
    fi

    # regex matches separated by |
    supported_distro_versions="7\.[0-9]+"
    if [[ ! $TEST_DISTRO_VERSION =~ $supported_distro_versions ]] && ([ -z "$UPGRADE_TEST_DISTRO" ] || [[ ! $UPGRADE_TEST_DISTRO =~ $supported_distro_versions ]]); then
      fake_test_pass "tests_skipped_because_unsupported_distro_$TEST_DISTRO_VERSION" "$WORKSPACE/test_reports/" ${BUILD_NUMBER}
      exit 0
    fi
}  # end of check_for_autopass()
