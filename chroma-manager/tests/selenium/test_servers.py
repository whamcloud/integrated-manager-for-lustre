from views.servers import Servers
from base import SeleniumBaseTestCase
from utils.sample_data import Testdata
from views.volumes import Volumes
from base import enter_text_for_element
from base import wait_for_element


class TestServer(SeleniumBaseTestCase):
    """Test cases for server related operations"""
    def setUp(self):
        super(TestServer, self).setUp()

        self.navigation.go('Configure', 'Servers')

        self.server_page = Servers(self.driver)

        # Getting test data for servers
        self.test_data = Testdata()
        self.host_list = self.test_data.get_test_data_for_server_configuration()

    def test_create_server(self):
        """Test server creation"""

        for host in self.host_list:
            self.server_page.new_add_server_button.click()
            host_name = host["address"]

            enter_text_for_element(self.driver, self.server_page.host_address_text, host_name)
            self.server_page.host_continue_button.click()

            # Verifying that add server confirm dialog is displayed
            self.assertTrue(wait_for_element(self.driver, self.server_page.confirm_dialog_div, 10), 'Add server confirm dialog not displayed')

            self.server_page.add_host_confirm_button.click()

            # Verifying that add server complete dialog is displayed
            self.assertTrue(wait_for_element(self.driver, self.server_page.complete_dialog_div, 10), 'Add server complete dialog not displayed')

            self.server_page.add_host_close_button.click()

            self.navigation.go('Volumes', 'Servers')

            self.server_page = Servers(self.driver)
            # Verifying that added server is displayed in server configuration list
            self.assertTrue(self.server_page.verify_added_server(host_name), 'Added server not displayed in server configuration list')

            # Check LNet state
            self.assertEqual('lnet_up', self.server_page.get_lnet_state(host_name), 'Incorrect LNet state')

    def test_volume_config_for_added_server(self):
        """Test for verifying that volumes appear for newly added server"""

        self.navigation.go('Volumes')
        volumes_page = Volumes(self.driver)

        for host in self.host_list:
            host_name = host["address"]

            # Verifying that volume configuration appear for added server
            self.assertTrue(volumes_page.get_volumes_for_added_server(host_name), 'Volumes not recognized for server: ' + host_name)

    def test_stop_lnet_on_server(self):
        """Test for Stopping LNet on server"""

        for host in self.host_list:
            host_name = host["address"]
            self.server_page.stop_lnet(host_name)

            # Check LNet state
            self.assertEqual('lnet_down', self.server_page.get_lnet_state(host_name), 'LNet not stopped')

    def test_start_lnet_on_server(self):
        """Test for Starting LNet on server"""

        for host in self.host_list:
            host_name = host["address"]

            self.server_page.start_lnet(host_name)

            # Check LNet state
            self.assertEqual('lnet_up', self.server_page.get_lnet_state(host_name), 'LNet not started')

    def test_unload_lnet_on_server(self):
        """Test for Unloading LNet on server"""

        for host in self.host_list:
            host_name = host["address"]

            self.server_page.unload_lnet(host_name)

            # Check LNet state
            self.assertEqual('lnet_unloaded', self.server_page.get_lnet_state(host_name), 'LNet not unloaded')

    def test_load_lnet_on_server(self):
        """Test for Loading LNet on server"""

        for host in self.host_list:
            host_name = host["address"]

            self.server_page.load_lnet(host_name)

            # Check LNet state
            self.assertEqual('lnet_down', self.server_page.get_lnet_state(host_name), 'LNet not loaded')

    def test_remove_server(self):
        """Test for Removing server"""

        for host in self.host_list:
            host_name = host["address"]

            self.server_page.remove_server(host_name)

            # Check LNet state
            self.assertEqual('lnet_unloaded', self.server_page.get_lnet_state(host_name), 'Server not removed')

import django.utils.unittest
if __name__ == '__main__':
    django.utils.unittest.main()
