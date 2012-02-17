""" Create file system test cases"""

from utils.navigation import Navigation
from views.create_filesystem import Filesystem
from base import SeleniumBaseTestCase
from utils.messages_text import Messages
from uitls.sample_data import Testdata


class CreateFileSystem(SeleniumBaseTestCase):

    def setUp(self):
        super(CreateFileSystem, self).setUp()
        self.test_data = Testdata()
        self.fs_test_data = self.fs_test_data.get_test_data_for_filesystem_configuration()

        self.file_system_name = self.fs_test_data['name']
        self.mgt_name = self.fs_test_data['mgs']
        self.mdt_host_name = self.fs_test_data['mdt']['mounts']['host']
        self.mdt_device_node = self.fs_test_data['mdt']['mounts']['device_node']
        self.ost_host_name = self.fs_test_data['ost']['mounts']['host']
        self.ost_device_node = self.fs_test_data['ost']['mounts']['device_node']

        self.page_navigation = Navigation(self.driver)
        self.page_navigation.click(self.page_navigation.links['Configure'])
        self.page_navigation.click(self.page_navigation.links['Create_new_filesystem'])
        self.message_text = Messages()
        self.create_filesystem_page = Filesystem(self.driver)

    def test_create_file_system(self):
        self.create_filesystem_page.enter_filesystem_name(self.file_system_name)
        self.create_filesystem_page.select_mgt(self.mgt_name)
        self.create_filesystem_page.select_mdt(self.mdt_host_name, self.mdt_device_node)
        self.create_filesystem_page.select_ost(self.ost_host_name, self.ost_device_node)
        self.create_filesystem_page.click_create_file_system_button()
        self.assertTrue(self.create_filesystem_page.file_system_list_displayed(), 'List of all file systems list is not displayed')
        self.assertTrue(self.create_filesystem_page.new_file_system_name_displayed(), 'File system list does not contain newly created file system')

    def test_blank_filesystem_name(self):
        """Test create file system by giving blank filesystem name"""
        self.create_filesystem_page.click_create_file_system_button()
        actual_message = self.create_filesystem_page.error_dialog_message()
        self.assertTrue(self.create_filesystem_page.error_dialog_displayed(), 'Error dialog is not displayed for blank filesyetem name')
        self.assertEqual(self.messages_text.get_message('file_systemname_blank'), actual_message, 'Error message for blank filesystem name is not displayed')

    def test_mgt_not_selected(self):
        """Test create file system by not selecting MGT"""
        self.create_filesystem_page.enter_filesystem_name(self.file_system_name)
        self.create_filesystem_page.click_create_file_system_button()
        actual_message = self.create_filesystem_page.error_dialog_message()
        self.assertTrue(self.create_filesystem_page.error_dialog_displayed(), 'Error dialog is not displayed for not selecting MGT')
        self.assertEqual(self.messages_text.get_message('mgt_not_selected'), actual_message, 'Error message for not selecting MGT is not displayed')

    def test_mdt_not_selected(self):
        """Test create file system by not selecting MDT"""
        self.create_filesystem_page.enter_filesystem_name(self.file_system_name)
        self.create_filesystem_page.select_mgt(self.mgt_name)
        self.create_filesystem_page.click_create_file_system_button()
        actual_message = self.create_filesystem_page.error_dialog_message()
        self.assertTrue(self.create_filesystem_page.error_dialog_displayed(), 'Error dialog is not displayed for not selecting MDT')
        self.assertEqual(self.messages_text.get_message('mdt_not_selected'), actual_message, 'Error message for not selecting MDT is not displayed')

    def test_ost_not_selected(self):
        """Test create file system by not selecting OST"""
        self.create_filesystem_page.enter_filesystem_name(self.file_system_name)
        self.create_filesystem_page.select_mgt(self.mgt_name)
        self.create_filesystem_page.select_mdt(self.mdt_host_name, self.mdt_device_node)
        self.create_filesystem_page.click_create_file_system_button()
        actual_message = self.create_filesystem_page.error_dialog_message()
        self.assertTrue(self.create_filesystem_page.error_dialog_displayed(), 'Error dialog is not displayed for not selecting OST')
        self.assertEqual(self.messages_text.get_message('ost_not_selected'), actual_message, 'Error message for not selecting OST is not displayed')

import unittest
if __name__ == '__main__':
    unittest.main()
