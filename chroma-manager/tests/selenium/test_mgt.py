#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import django.utils.unittest
from views.mgt import Mgt
from views.servers import Servers
from base import SeleniumBaseTestCase
from utils.constants import static_text
from utils.constants import wait_time
from utils.sample_data import Testdata
from base import wait_for_element
from base import wait_for_datatable


class TestMgt(SeleniumBaseTestCase):
    """Test cases for MGT operations"""

    def setUp(self):
        super(TestMgt, self).setUp()

        self.medium_wait = wait_time['medium']
        self.long_wait = wait_time['long']

        self.navigation.go('Configure', 'Servers')

        self.test_data = Testdata()

        # Test data for servers
        self.host_list = self.test_data.get_test_data_for_server_configuration()
        wait_for_datatable(self.driver, '#server_configuration')
        self.server_page = Servers(self.driver)
        self.server_page.add_servers(self.host_list)

        # Test data for MGT
        self.mgt_host_name = self.host_list[0]['address']
        self.mgt_device_node = self.host_list[0]['device_node'][0]

        self.navigation.go('Configure', 'MGTs')
        wait_for_element(self.driver, 'span.volume_chooser_selected', self.medium_wait)

    def test_create_mgt(self):
        """Test MGT creation"""

        mgt_page = Mgt(self.driver)
        mgt_page.create_mgt(self.mgt_host_name, self.mgt_device_node)
        self.driver.refresh()
        wait_for_datatable(self.driver, '#mgt_configuration')
        mgt_page = Mgt(self.driver)
        self.assertTrue(mgt_page.verify_added_mgt(self.mgt_host_name, self.mgt_device_node), 'Added MGT not in list')

    def test_create_button_visibility_without_selecting_storage(self):
        """Test Create MGT button visibility without selecting storage"""

        mgt_page = Mgt(self.driver)
        mgt_page.create_mgt(self.mgt_host_name, self.mgt_device_node)
        self.driver.refresh()
        wait_for_datatable(self.driver, '#mgt_configuration')
        mgt_page = Mgt(self.driver)
        # Verifying that create mgt button remains disabled without selecting storage
        self.assertFalse(mgt_page.create_mgt_button.is_enabled(), 'Button for creating MGT is enabled without selecting volume')

    def test_start_and_stop_mgt(self):
        """Test starting and stopping an MGT"""
        mgt_page = Mgt(self.driver)
        mgt_page.create_mgt(self.mgt_host_name, self.mgt_device_node)
        self.driver.refresh()
        wait_for_datatable(self.driver, '#mgt_configuration')
        self.stop_mgt()
        self.start_mgt()
        self.driver.refresh()
        wait_for_datatable(self.driver, '#mgt_configuration')

    def create_mgt(self):
        mgt_page = Mgt(self.driver)
        mgt_page.create_mgt(self.mgt_host_name, self.mgt_device_node)

    def stop_mgt(self):
        mgt_page = Mgt(self.driver)
        mgt_page.transition(self.mgt_host_name, self.mgt_device_node, static_text['stop_mgt'])
        self.assertFalse(mgt_page.check_action_available(self.mgt_host_name, self.mgt_device_node, static_text['stop_mgt']))

    def start_mgt(self):
        mgt_page = Mgt(self.driver)
        mgt_page.transition(self.mgt_host_name, self.mgt_device_node, static_text['start_mgt'], False)
        self.assertFalse(mgt_page.check_action_available(self.mgt_host_name, self.mgt_device_node, static_text['start_mgt']))

    def tearDown(self):
        mgt_page = Mgt(self.driver)
        mgt_page.transition(self.mgt_host_name, self.mgt_device_node, static_text['remove_mgt'])

        self.navigation.go('Configure', 'Servers')
        self.server_page = Servers(self.driver)
        wait_for_datatable(self.driver, '#server_configuration')
        self.server_page.remove_servers(self.host_list)

        super(TestMgt, self).tearDown()

if __name__ == '__main__':
    django.utils.unittest.main()
