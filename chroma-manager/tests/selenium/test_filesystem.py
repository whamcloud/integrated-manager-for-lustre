#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import django.utils.unittest
from views.filesystem import Filesystem
from base import SeleniumBaseTestCase
from utils.sample_data import Testdata
from utils.constants import static_text
from base import wait_for_datatable
from views.mgt import Mgt
from views.servers import Servers
from views.create_filesystem import CreateFilesystem
from base import wait_for_element
from utils.constants import wait_time


class TestFilesystem(SeleniumBaseTestCase):
    """Test cases for file system related operations"""

    def setUp(self):
        super(TestFilesystem, self).setUp()

        self.medium_wait = wait_time['medium']
        self.test_data = Testdata()

        # Test data for servers
        self.host_list = self.test_data.get_test_data_for_server_configuration()

        # Test data for MGT
        self.mgt_test_data = self.test_data.get_test_data_for_mgt_configuration()
        self.mgt_host_name = self.mgt_test_data[0]['mounts'][0]['host']
        self.mgt_device_node = self.mgt_test_data[0]['mounts'][0]['device_node']

        # Test data for file system
        self.fs_test_data = self.test_data.get_test_data_for_filesystem_configuration()
        self.filesystem_name = self.fs_test_data[0]['name']
        self.mgt_name = self.fs_test_data[0]['mgt']
        self.mdt_host_name = self.fs_test_data[0]['mdt']['mounts'][0]['host']
        self.mdt_device_node = self.fs_test_data[0]['mdt']['mounts'][0]['device_node']
        self.ost_host_name = self.fs_test_data[0]['osts'][0]['mounts'][0]['host']
        self.ost_device_node = self.fs_test_data[0]['osts'][0]['mounts'][0]['device_node']
        self.conf_params = self.fs_test_data[0]['conf_params']

        # Add server
        self.navigation.go('Configure', 'Servers')
        wait_for_datatable(self.driver, '#server_configuration')
        self.server_page = Servers(self.driver)
        self.server_page.add_servers(self.host_list)

        # Create MGT
        self.navigation.go('Configure', 'MGTs')
        self.driver.refresh()
        wait_for_datatable(self.driver, '#mgt_configuration')
        wait_for_element(self.driver, 'span.volume_chooser_selected', self.medium_wait)
        self.mgt_page = Mgt(self.driver)
        self.mgt_page.create_mgt(self.mgt_host_name, self.mgt_device_node)

        # Create filesystem
        self.navigation.go('Configure', 'Create_new_filesystem')
        wait_for_element(self.driver, "#btnCreateFS", self.medium_wait)
        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.create(self.filesystem_name, self.mgt_name, self.mdt_host_name, self.mdt_device_node, self.ost_host_name, self.ost_device_node, self.conf_params)

        # Test data for filesystem
        self.fs_list = self.test_data.get_test_data_for_filesystem_configuration()

        self.navigation.go('Configure')
        wait_for_datatable(self.driver, '#fs_list')

    def test_filesystem_start_and_stop(self):
        """Test for starting and stopping file system"""

        fs_page = Filesystem(self.driver)

        wait_for_datatable(self.driver, '#fs_list')
        for fs in self.fs_list:
            fs_page.transition(fs['name'], static_text['stop_fs'])
            fs_page.check_action_available(fs['name'], static_text['stop_fs'])

            self.driver.refresh()
            wait_for_datatable(self.driver, '#fs_list')
            fs_page = Filesystem(self.driver)

            fs_page.transition(fs['name'], static_text['start_fs'], False)
            fs_page.check_action_available(fs['name'], static_text['start_fs'])

    def tearDown(self):
        self.navigation.go('Configure')
        fs_page = Filesystem(self.driver)
        wait_for_datatable(self.driver, '#fs_list')
        fs_page.transition(self.filesystem_name, static_text['remove_fs'])

        self.navigation.go('Configure', 'MGTs')
        self.driver.refresh()
        wait_for_datatable(self.driver, '#mgt_configuration')
        mgt_page = Mgt(self.driver)
        mgt_page.transition(self.mgt_host_name, self.mgt_device_node, static_text['remove_mgt'])

        self.navigation.go('Configure', 'Servers')
        self.driver.refresh()
        server_page = Servers(self.driver)
        wait_for_datatable(self.driver, '#server_configuration')
        server_page.remove_servers(self.host_list)

        self.driver.close()

if __name__ == '__main__':
    django.utils.unittest.main()
