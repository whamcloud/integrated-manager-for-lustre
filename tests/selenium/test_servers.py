""" Create mgt test cases"""

from utils.navigation import Navigation
from views.servers import Servers
from base import SeleniumBaseTestCase


class CreateServer(SeleniumBaseTestCase):
    def test_create_mgt(self):
        #Create a file_system : Positive Test

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation._links['Configure'])
        page_navigation.click(page_navigation._links['Servers'])

        # Calling create_server
        create_server_page = Servers(self.driver)

        create_server_page.click_new_server_add_button()
        create_server_page.enter_hostname()
        create_server_page.click_continue_button()

        # Verifying that add server confirm dialog list is displayed
        self.assertTrue(create_server_page.confirm_div_displayed(), 'Add server confirm div not displayed')

        create_server_page.click_confirm_button()

        # Verifying that add server complete dialog list is displayed
        self.assertTrue(create_server_page.complete_div_displayed(), 'Add server complete div not displayed')

        create_server_page.click_close_button()

import unittest
if __name__ == '__main__':
    unittest.main()
