""" Create file system test cases"""

from utils.navigation import Navigation
from views.create_filesystem import FileSystem
from base import SeleniumBaseTestCase
from utils.messages_text import Messages


class CreateFileSystem(SeleniumBaseTestCase):

    #FIXME - File system name to be given from config file
    """def test_create_file_system(self):
        Create a file_system : Positive Test

        Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Create_new_filesystem'])

        Calling create_file_system
        create_filesystem_page = FileSystem(self.driver)

        create_filesystem_page.enter_filesystem_data()

        create_filesystem_page.click_create_file_system_button()

        Verifying that file system list is displayed
        self.assertTrue(create_filesystem_page.file_system_list_displayed(), 'List of all file systems list is not displayed')

        Verifying that the newly created file system is visible in all file system list
        self.assertTrue(create_filesystem_page.new_file_system_name_displayed(), 'File system list does not contain newly created file system')
    """

    def test_blank_filesystem_name(self):
        """Test create file system by giving blank filesystem name"""

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Create_new_filesystem'])

        # Calling create_file_system
        create_filesystem_page = FileSystem(self.driver)

        create_filesystem_page.click_create_file_system_button()

        # Verifying the error dialog being displayed
        messages = Messages()
        actual_message = create_filesystem_page.error_dialog_message()
        self.assertTrue(create_filesystem_page.error_dialog_displayed(), 'Error dialog is not displayed for blank filesyetem name')
        self.assertEqual(messages.get_message('file_systemname_blank'), actual_message, 'Error message for blank filesystem name is not displayed')

    def test_mgt_not_selected(self):
        """Test create file system by not selecting MGT"""

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Create_new_filesystem'])

        # Calling create_file_system
        create_filesystem_page = FileSystem(self.driver)

        create_filesystem_page.enter_filename()
        create_filesystem_page.click_create_file_system_button()

        # Verifying the error dialog being displayed
        messages = Messages()
        actual_message = create_filesystem_page.error_dialog_message()
        self.assertTrue(create_filesystem_page.error_dialog_displayed(), 'Error dialog is not displayed for not selecting MGT')
        self.assertEqual(messages.get_message('mgt_not_selected'), actual_message, 'Error message for not selecting MGT is not displayed')

    def test_mdt_not_selected(self):
        """Test create file system by not selecting MDT"""

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Create_new_filesystem'])

        # Calling create_file_system
        create_filesystem_page = FileSystem(self.driver)

        create_filesystem_page.enter_filename()
        create_filesystem_page.select_mgt()
        create_filesystem_page.click_create_file_system_button()

        # Verifying the error dialog being displayed
        messages = Messages()
        actual_message = create_filesystem_page.error_dialog_message()
        self.assertTrue(create_filesystem_page.error_dialog_displayed(), 'Error dialog is not displayed for not selecting MDT')
        self.assertEqual(messages.get_message('mdt_not_selected'), actual_message, 'Error message for not selecting MDT is not displayed')

    def test_ost_not_selected(self):
        """Test create file system by not selecting OST"""

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Create_new_filesystem'])

        # Calling create_file_system
        create_filesystem_page = FileSystem(self.driver)

        create_filesystem_page.enter_filename()
        create_filesystem_page.select_mgt()
        create_filesystem_page.select_mdt()
        create_filesystem_page.click_create_file_system_button()

        # Verifying the error dialog being displayed
        messages = Messages()
        actual_message = create_filesystem_page.error_dialog_message()
        self.assertTrue(create_filesystem_page.error_dialog_displayed(), 'Error dialog is not displayed for not selecting OST')
        self.assertEqual(messages.get_message('ost_not_selected'), actual_message, 'Error message for not selecting OST is not displayed')

import unittest
if __name__ == '__main__':
    unittest.main()
