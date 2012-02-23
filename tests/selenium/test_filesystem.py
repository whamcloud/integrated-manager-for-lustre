""" Create file system test cases"""

from utils.navigation import Navigation
from views.filesystem import Filesystem
from base import SeleniumBaseTestCase
from utils.sample_data import Testdata
from utils.messages_text import Messages


class TestFilesystem(SeleniumBaseTestCase):

    def setUp(self):
        super(TestFilesystem, self).setUp()
        self.test_data = Testdata()
        self.fs_list = self.fs_test_data.get_test_data_for_filesystem_configuration()
        self.fs_page = Filesystem()
        self.page_navigation = Navigation(self.driver)
        self.page_navigation.click(self.page_navigation.links['Configure'])
        self.message_text = Messages()

    def test_filesystem_stop(self):
        for fs in self.fs_list:
            self.fs_page.stop_fs(fs['name'])
            self.assertFalse(self.fs_page.check_fs_actions(self.message_text.get_message('stop_action_text')))

    def test_filesystem_start(self):
        for fs in self.fs_list:
            self.fs_page.start_fs(fs['name'])
            self.assertFalse(self.fs_page.check_fs_actions(self.message_text.get_message('start_action_text')))

    def test_filesystem_remove(self):
        for fs in self.fs_list:
            self.fs_page.remove_fs(fs['name'])
            self.assertFalse(self.fs_page.check_fs_actions(self.message_text.get_message('remove_action_text')))

    def test_add_ost(self):
        for fs in self.fs_list:
            self.fs_page.edit_fs_action(fs['name'])
            ost_host_name = fs['osts'][0]['mounts'][0]['host']
            ost_device_node = fs['osts'][0]['mounts'][0]['device_node']
            self.fs_page.select_ost(ost_host_name, ost_device_node)

import unittest
if __name__ == '__main__':
    unittest.main()
