#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from tests.selenium.views.filesystem import Filesystem
from tests.selenium.base import SeleniumBaseTestCase, wait_for_transition
from utils.sample_data import Testdata
from tests.selenium.utils.constants import static_text


class TestFilesystem(SeleniumBaseTestCase):
    """Test cases for file system related operations"""

    def setUp(self):
        super(TestFilesystem, self).setUp()

        self.test_data = Testdata()
        self.host_list = self.test_data.get_test_data_for_server_configuration()
        self.fs_test_data = self.test_data.get_test_data_for_filesystem_configuration()
        self.filesystem_name = self.fs_test_data['name']

        self.create_filesystem_simple(self.host_list, self.filesystem_name)

        self.navigation.go('Configure', 'Filesystems')

    def test_filesystem_start_and_stop(self):
        """Test for starting and stopping file system"""

        fs_page = Filesystem(self.driver)

        fs_page.transition(self.filesystem_name, static_text['stop_fs'])
        fs_page.check_action_unavailable(self.filesystem_name, static_text['stop_fs'])

        wait_for_transition(self.driver, self.standard_wait)

        fs_page.transition(self.filesystem_name, static_text['start_fs'], False)
        fs_page.check_action_unavailable(self.filesystem_name, static_text['start_fs'])
