# This file will selectively autopass some commits.

# At present bumps to the GUI only are auto passed.

. chroma-manager/tests/framework/utils/gui_update.sh
. chroma-manager/tests/framework/utils/fake_pass.sh

if gui_bump; then
  fake_test_pass "tests_skipped_because_gui_version_bump" "$WORKSPACE/test_reports/" ${BUILD_NUMBER}
  exit 0
fi
