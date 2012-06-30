#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from tests.selenium.views.servers import Servers
from tests.selenium.base import SeleniumBaseTestCase
from tests.selenium.utils.constants import static_text
from tests.selenium.utils.constants import wait_time
from utils.sample_data import Testdata
from tests.selenium.views.volumes import Volumes


class TestServer(SeleniumBaseTestCase):
    """Test cases for server related operations"""
    def setUp(self):
        super(TestServer, self).setUp()

        self.long_wait = wait_time['long']
        self.medium_wait = wait_time['medium']

        # Getting test data for servers
        self.test_data = Testdata()
        self.host_list = self.test_data.get_test_data_for_server_configuration()

        self.navigation.go('Configure', 'Servers')
        self.server_page = Servers(self.driver)

    def test_create_server(self):
        self.server_page.add_servers(self.host_list)
        self.navigation.go('Volumes', 'Servers')
        for host in self.host_list:
            host_name = host["address"]
            # Check LNet state
            self.assertEqual('LNet up', self.server_page.get_lnet_state(host_name))

    def test_volume_config_for_added_server(self):
        """Test for verifying that volumes appear for newly added server"""

        self.server_page.add_servers(self.host_list)
        self.check_volume_config_for_added_server()
        self.navigation.go('Servers')

    def test_start_and_stop_lnet_on_server(self):
        """Test for starting and stopping LNet on server"""

        self.server_page.add_servers(self.host_list)
        self.stop_lnet_on_servers()
        self.start_lnet_on_servers()

    def test_load_and_unload_lnet_on_server(self):
        """Test for loading and unloading LNet on server"""

        self.server_page.add_servers(self.host_list)
        self.unload_lnet_on_servers()
        self.load_lnet_on_servers()

    def check_volume_config_for_added_server(self):
        self.navigation.go('Volumes')
        volumes_page = Volumes(self.driver)

        for host in self.host_list:
            host_name = host["address"]

            # Verifying that volume configuration appear for added server
            self.assertTrue(volumes_page.check_primary_volumes(host_name), 'Volumes not recognized for server: ' + host_name)

    def stop_lnet_on_servers(self):
        for host in self.host_list:
            host_name = host["address"]
            self.server_page.transition(host_name, static_text['stop_lnet'])

            # Check LNet state
            self.assertEqual('lnet_down', self.server_page.get_lnet_state(host_name), 'LNet not stopped')

    def start_lnet_on_servers(self):
        for host in self.host_list:
            host_name = host["address"]
            self.server_page.transition(host_name, static_text['start_lnet'])

            # Check LNet state
            self.assertEqual('lnet_up', self.server_page.get_lnet_state(host_name), 'LNet not started')

    def unload_lnet_on_servers(self):
        for host in self.host_list:
            host_name = host["address"]
            self.server_page.transition(host_name, static_text['unload_lnet'])

            # Check LNet state
            self.assertEqual('lnet_unloaded', self.server_page.get_lnet_state(host_name), 'LNet not unloaded')

    def load_lnet_on_servers(self):
        for host in self.host_list:
            host_name = host["address"]
            self.server_page.transition(host_name, static_text['load_lnet'])

            # Check LNet state
            self.assertEqual('lnet_down', self.server_page.get_lnet_state(host_name), 'LNet not loaded')
