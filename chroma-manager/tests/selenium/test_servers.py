from tests.selenium.views.command_detail import CommandDetail

from tests.selenium.views.servers import Servers
from tests.selenium.base import SeleniumBaseTestCase
from utils.sample_data import Testdata
from tests.selenium.views.volumes import Volumes


class TestServer(SeleniumBaseTestCase):
    """Test cases for server related operations"""
    def setUp(self):
        super(TestServer, self).setUp()

        # Getting test data for servers
        self.test_data = Testdata()
        self.host_list = self.test_data.get_test_data_for_server_configuration()

        self.navigation.go('Configure', 'Servers')
        self.server_page = Servers(self.driver)

    def test_multi_server_operations(self):
        self.server_page.add_servers(self.host_list)

        # Check that the prompt dialog opens
        self.server_page.open_detect_prompt()
        self.assertTrue(self.server_page.host_selection_list_visible)

        # Check that all hosts are listed
        self.assertSetEqual(set(self.server_page.host_selection_list_selected.keys()), set(self.server_page.get_server_list()))

        # Check that all are selected by default
        self.assertSetEqual(set(self.server_page.host_selection_list_selected.values()), set([True]))
        self.assertTrue(self.server_page.host_selection_run_sensitive)

        # Check that select none clears all
        self.server_page.host_selection_list_none()
        self.assertSetEqual(set(self.server_page.host_selection_list_selected.values()), set([False]))

        # ...and that when none are selected the run button is disabled
        self.assertFalse(self.server_page.host_selection_run_sensitive)

        # Check that select all works
        self.server_page.host_selection_list_all()
        self.assertSetEqual(set(self.server_page.host_selection_list_selected.values()), set([True]))
        self.assertTrue(self.server_page.host_selection_run_sensitive)

        # Check that on run we go to a command detail view
        self.server_page.host_selection_run()

        command_detail = CommandDetail(self.driver)
        self.assertTrue(command_detail.visible)

    def test_create_server(self):
        self.server_page.add_servers(self.host_list)
        self.navigation.go('Configure', 'Servers')
        for host in self.host_list:
            host_name = host["address"]
            # Check LNet state
            self.assertEqual('LNet up', self.server_page.get_lnet_state(host_name))

    def test_create_server_validation(self):
        # Enter something invalid, check a validation message appears
        self.server_page.add_server_open()
        self.server_page.add_server_enter_address("")
        self.server_page.add_server_submit_address()
        self.assertEqual(self.server_page.add_server_error, "This field is mandatory")

        # Enter something valid, complete adding and opt to add another
        self.server_page.add_server_enter_address(self.host_list[0]['address'])
        self.server_page.add_server_select_profile()
        self.server_page.add_server_submit_address()
        self.server_page.add_server_confirm()
        self.server_page.add_server_add_another()

        # Check that the validation message is not visible
        self.assertEqual(self.server_page.add_server_error, None)

    def test_volume_config_for_added_server(self):
        """Test for verifying that volumes appear for newly added server"""

        self.server_page.add_servers(self.host_list)
        self.check_volume_config_for_added_server()
        self.navigation.go('Configure', 'Servers')

    def test_start_and_stop_lnet_on_server(self):
        """Test for starting and stopping LNet on server"""

        address = self.host_list[0]['address']
        self.server_page.add_servers(self.host_list)
        self.server_page.transition(address, 'lnet_down')
        self.assertEqual(self.server_page.get_lnet_state(address), "LNet down")
        self.server_page.transition(address, 'lnet_up')
        self.assertEqual(self.server_page.get_lnet_state(address), "LNet up")

    def test_load_and_unload_lnet_on_server(self):
        """Test for loading and unloading LNet on server"""

        address = self.host_list[0]['address']
        self.server_page.add_servers(self.host_list)
        self.server_page.transition(address, 'lnet_unloaded')
        self.assertEqual(self.server_page.get_lnet_state(address), "LNet unloaded")
        self.server_page.transition(address, 'lnet_down')
        self.assertEqual(self.server_page.get_lnet_state(address), "LNet down")

    def test_remove_server(self):
        victim = self.host_list[0]['address']

        # Add N servers
        self.server_page.add_servers(self.host_list)
        self.assertTrue(self.server_page.server_visible(victim))
        self.assertEqual(len(self.server_page.get_server_list()), len(self.host_list))
        # Remove one of the servers
        self.server_page.transition(victim, 'removed')
        self.assertFalse(self.server_page.server_visible(victim))
        self.assertEqual(len(self.server_page.get_server_list()), len(self.host_list) - 1)

    def check_volume_config_for_added_server(self):
        self.navigation.go('Configure', 'Volumes')
        volumes_page = Volumes(self.driver)

        for host in self.host_list:
            host_name = host["address"]

            # Verifying that volume configuration appear for added server
            self.assertTrue(volumes_page.check_primary_volumes(host_name), 'Volumes not recognized for server: ' + host_name)
