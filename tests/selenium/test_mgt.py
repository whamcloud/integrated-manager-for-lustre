""" Create mgt test cases"""

from utils.navigation import Navigation
from views.mgt import Mgt
from base import SeleniumBaseTestCase


class CreateFileSystem(SeleniumBaseTestCase):
    def test_create_mgt(self):
        #Create a MGT

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation._links['Configure'])
        page_navigation.click(page_navigation._links['MGTs'])

        # Calling create_mgt
        create_mgt_page = Mgt(self.driver)

        create_mgt_page.select_mgt()

        create_mgt_page.click_create_mgt()

        # Verifying that mgt list is displayed
        self.assertTrue(create_mgt_page.mgt_list_displayed(), 'MGT list is not displayed')

        # Verifying that there are no errors while creating MGT
        self.assertFalse(create_mgt_page.error_dialog_displayed(), 'Error in creating MGT')

    def test_create_mgt_without_selecting_storage(self):
        """Test create MGT button visibility without selecting storage"""

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation._links['Configure'])
        page_navigation.click(page_navigation._links['MGTs'])

        # Calling create_mgt
        create_mgt_page = Mgt(self.driver)

        # Verifying that create mgt button is not enabled without selecting storage
        self.assertFalse(create_mgt_page.create_mgt_button_enabled(), 'Create MGT button is displayed without selecting volume')

import unittest
if __name__ == '__main__':
    unittest.main()
