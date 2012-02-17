""" Create mgt test cases"""

from utils.navigation import Navigation
from views.mgt import Mgt
from base import SeleniumBaseTestCase


class TestMgt(SeleniumBaseTestCase):

    def setUp(self):
        super(TestMgt, self).setUp()
        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['MGTs'])
        # Calling create_mgt
        self.create_mgt_page = Mgt(self.driver)
        self.created_mgt_host = ""

    def test_create_mgt(self):
        self.create_mgt_page.select_mgt()
        self.create_mgt_page.create_mgt()
        # Verifying that mgt list is displayed
        self.assertTrue(self.create_mgt_page.mgt_list_displayed(), 'MGT list is not displayed')
        # Verifying that there are no errors while creating MGT
        self.assertFalse(self.create_mgt_page.error_dialog_displayed(), 'Error in creating MGT')
        self.created_mgt_host = self.create_mgt_page.selected_mgt_host

    def test_create_mgt_without_selecting_storage(self):
        """Test create MGT button visibility without selecting storage"""
        # FIXME: Navigation should know what to wait for when going
        # to a new page (in the case of dynamically loaded tabs you
        # have to poll for this)
        from base import wait_for_element
        wait_for_element(self.driver, '#btnNewMGT', 10)
        # Calling create_mgt
        self.create_mgt_page = Mgt(self.driver)
        # Verifying that create mgt button is not enabled without selecting storage
        self.assertFalse(self.create_mgt_page.create_mgt_button_enabled(), 'Create MGT button is displayed without selecting volume')

    def test_stop_mgt(self):
        self.create_mgt_page.stop_mgt(self.created_mgt_host)
        self.assertFalse(self.create_mgt_page.check_mgt_actions('Stop'))

    def test_start_mgt(self):
        self.create_mgt_page.start_mgt(self.created_mgt_host)
        self.assertFalse(self.create_mgt_page.check_mgt_actions('Start'))

    def test_remove_mgt(self):
        self.create_mgt_page.remove_mgt(self.created_mgt_host)
        self.assertFalse(self.create_mgt_page.check_mgt_actions('Remove'))

import unittest
if __name__ == '__main__':
    unittest.main()
