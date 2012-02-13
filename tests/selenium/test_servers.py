""" Create server test cases"""

from utils.navigation import Navigation
from views.servers import Servers
from base import SeleniumBaseTestCase
from utils.sample_data import Testdata


class CreateServer(SeleniumBaseTestCase):

    def test_create_server(self):
        # Create a server : Positive Test

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Servers'])

        # Calling create_server
        create_server_page = Servers(self.driver)

        # Getting test_data
        test_data = Testdata()
        host_list = test_data.data["hosts"]

        for i in xrange(len(host_list)):
            create_server_page.click_new_server_add_button()
            host_name = host_list[i]["name"]

            create_server_page.enter_hostname(host_name)
            create_server_page.click_continue_button()

            # Verifying that add server confirm dialog list is displayed
            self.assertTrue(create_server_page.confirm_div_displayed(), 'Add server confirm div not displayed')

            create_server_page.click_confirm_button()

            # Verifying that add server complete dialog list is displayed
            self.assertTrue(create_server_page.complete_div_displayed(), 'Add server complete div not displayed')

            create_server_page.click_close_button()

            # Verifying that added server is displayed in list
            self.assertTrue(create_server_page.verify_added_server(host_name), 'Added server not displayed in server configuration list')

            # Check LNet state
            self.assertEqual('lnet_up', create_server_page.get_lnet_state(host_name), 'Incorrect LNet state')

    """def stop_lnet_on_server(self):
        Create a file_system : Positive Test

         Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Servers'])

         Calling create_server
        create_server_page = Servers(self.driver)

         Getting test_data
        test_data = Testdata()
        host_list = test_data.data["hosts"]

        for i in xrange(len(host_list)):
            create_server_page.click_new_server_add_button()
            host_name = host_list[i]["name"]

            create_server_page.stop_lnet(host_name)

            # Verifying the lnet state
            self.assertTrue('lnet_down', create_server_page.get_lnet_state(host_name), 'LNet not stopped')
    """

import unittest
if __name__ == '__main__':
    unittest.main()
