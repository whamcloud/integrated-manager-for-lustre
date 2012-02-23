""" Create server test cases"""

from utils.navigation import Navigation
from views.servers import Servers
from base import SeleniumBaseTestCase
from utils.sample_data import Testdata
from views.volumes import Volumes


class TestServer(SeleniumBaseTestCase):

    def setUp(self):
        super(TestServer, self).setUp()

    def test_create_server(self):
        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Servers'])

        # Calling create_server
        create_server_page = Servers(self.driver)

        # Getting test_data
        test_data = Testdata()
        host_list = test_data.get_test_data_for_server_configuration()

        for i in xrange(len(host_list)):
            create_server_page.click_new_server_add_button()
            host_name = host_list[i]["address"]

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

    def test_volume_config_for_added_server(self):

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Volumes'])

        # Calling volumes
        volumes_page = Volumes(self.driver)

        # Getting test_data
        test_data = Testdata()
        host_list = test_data.get_test_data_for_server_configuration()

        for i in xrange(len(host_list)):
            host_name = host_list[i]["address"]

            # Verifying that volume configuration appear for added server
            self.assertTrue(volumes_page.get_volumes_for_added_server(host_name), 'Volumes not recognized for server: ' + host_name)

    def test_stop_lnet_on_server(self):
        # Stop LNet on server

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Servers'])

        # Calling create_server
        create_server_page = Servers(self.driver)

        # Getting test_data
        test_data = Testdata()
        host_list = test_data.get_test_data_for_server_configuration()

        for i in xrange(len(host_list)):
            host_name = host_list[i]["address"]

            create_server_page.stop_lnet(host_name)

            # Verifying the lnet state
            self.assertEqual('lnet_down', create_server_page.get_lnet_state(host_name), 'LNet not stopped')

    def test_start_lnet_on_server(self):
        # Start LNet on server

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Servers'])

        # Calling create_server
        create_server_page = Servers(self.driver)

        # Getting test_data
        test_data = Testdata()
        host_list = test_data.get_test_data_for_server_configuration()

        for i in xrange(len(host_list)):
            host_name = host_list[i]["address"]

            create_server_page.start_lnet(host_name)

            # Verifying the lnet state
            self.assertEqual('lnet_up', create_server_page.get_lnet_state(host_name), 'LNet not started')

    def test_unload_lnet_on_server(self):
        # Unload LNet on server

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Servers'])

        # Calling create_server
        create_server_page = Servers(self.driver)

        # Getting test_data
        test_data = Testdata()
        host_list = test_data.get_test_data_for_server_configuration()

        for i in xrange(len(host_list)):
            host_name = host_list[i]["address"]

            create_server_page.unload_lnet(host_name)

            # Verifying the lnet state
            self.assertEqual('lnet_unloaded', create_server_page.get_lnet_state(host_name), 'LNet not unloaded')

    def test_load_lnet_on_server(self):
        # Load LNet on server

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Servers'])

        # Calling create_server
        create_server_page = Servers(self.driver)

        # Getting test_data
        test_data = Testdata()
        host_list = test_data.get_test_data_for_server_configuration()

        for i in xrange(len(host_list)):
            host_name = host_list[i]["address"]

            create_server_page.load_lnet(host_name)

            # Verifying the lnet state
            self.assertEqual('lnet_down', create_server_page.get_lnet_state(host_name), 'LNet not loaded')

    def test_remove_lnet_on_server(self):
        # Remove server

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])
        page_navigation.click(page_navigation.links['Servers'])

        # Calling create_server
        create_server_page = Servers(self.driver)

        # Getting test_data
        test_data = Testdata()
        host_list = test_data.get_test_data_for_server_configuration()

        for i in xrange(len(host_list)):
            host_name = host_list[i]["address"]

            create_server_page.remove_lnet(host_name)

            # Verifying the lnet state
            self.assertEqual('lnet_unloaded', create_server_page.get_lnet_state(host_name), 'Server not removed')

import unittest
if __name__ == '__main__':
    unittest.main()
