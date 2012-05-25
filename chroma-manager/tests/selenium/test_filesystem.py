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
from views.create_filesystem import CreateFilesystem
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

        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.create_filesystem_with_server_and_mgt(self.host_list, self.mgt_host_name, self.mgt_device_node, self.filesystem_name, self.mgt_name, self.mdt_host_name, self.mdt_device_node, self.ost_host_name, self.ost_device_node, self.conf_params)

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

        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.remove_filesystem_with_server_and_mgt(self.filesystem_name, self.mgt_host_name, self.mgt_device_node, self.host_list)

        super(TestFilesystem, self).tearDown()

if __name__ == '__main__':
    django.utils.unittest.main()
