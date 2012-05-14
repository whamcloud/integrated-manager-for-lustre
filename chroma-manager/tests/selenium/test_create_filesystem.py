#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import django.utils.unittest
from views.mgt import Mgt
from views.servers import Servers
from views.create_filesystem import CreateFilesystem
from views.filesystem import Filesystem
from utils.constants import wait_time
from utils.constants import static_text
from base import SeleniumBaseTestCase
from utils.messages_text import validation_messages
from utils.sample_data import Testdata
from base import enter_text_for_element
from base import wait_for_element
from base import element_visible
from base import wait_for_datatable


class TestCreateFileSystem(SeleniumBaseTestCase):
    """Test cases for file system creation and validations"""

    def setUp(self):
        super(TestCreateFileSystem, self).setUp()

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

        self.navigation.go('Configure', 'Create_new_filesystem')
        wait_for_element(self.driver, "#btnCreateFS", self.medium_wait)

    def test_create_filesystem(self):
        """Test case for creating file system"""

        self.navigation.go('Configure', 'Servers')
        wait_for_datatable(self.driver, '#server_configuration')
        self.server_page = Servers(self.driver)
        self.server_page.add_servers(self.host_list)

        self.navigation.go('Configure', 'MGTs')
        self.driver.refresh()
        wait_for_datatable(self.driver, '#mgt_configuration')
        self.mgt_page = Mgt(self.driver)
        self.mgt_page.create_mgt(self.mgt_host_name, self.mgt_device_node)

        self.navigation.go('Configure', 'Create_new_filesystem')
        wait_for_element(self.driver, "#btnCreateFS", self.medium_wait)
        self.driver.refresh()
        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.create(self.filesystem_name, self.mgt_name, self.mdt_host_name, self.mdt_device_node, self.ost_host_name, self.ost_device_node, self.conf_params)
        filesystem_create_message = create_filesystem_page.verify_created_filesystem(self.filesystem_name, self.mgt_name, self.mdt_host_name, self.mdt_device_node, self.ost_host_name, self.ost_device_node)
        self.assertEqual('', filesystem_create_message, filesystem_create_message)

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
        server_page = Servers(self.driver)
        wait_for_datatable(self.driver, '#server_configuration')
        server_page.remove_servers(self.host_list)

    def test_blank_filesystem_name(self):
        """Test create file system by giving blank filesystem name"""

        self.driver.refresh()
        wait_for_element(self.driver, "#btnCreateFS", self.medium_wait)
        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.create_filesystem_button.click()
        wait_for_element(self.driver, create_filesystem_page.error_span, self.medium_wait)
        actual_message = create_filesystem_page.validation_error_message(0)
        self.assertEqual(validation_messages['blank_filesystem_name'], actual_message, 'Error message for blank filesystem name is not displayed')

    def test_mgt_not_selected(self):
        """Test create file system without selecting MGT"""

        self.driver.refresh()
        wait_for_element(self.driver, "#btnCreateFS", self.medium_wait)
        create_filesystem_page = CreateFilesystem(self.driver)
        enter_text_for_element(self.driver, create_filesystem_page.filesystem_text, self.filesystem_name)
        create_filesystem_page.create_filesystem_button.click()
        wait_for_element(self.driver, create_filesystem_page.error_span, self.medium_wait)
        actual_message = create_filesystem_page.validation_error_message(0)
        self.assertEqual(validation_messages['mgt_not_selected'], actual_message, 'Error message for not selecting MGT is not displayed')

    def test_mdt_not_selected(self):
        """Test create file system without selecting MDT"""

        self.driver.refresh()
        wait_for_element(self.driver, "#btnCreateFS", self.medium_wait)
        create_filesystem_page = CreateFilesystem(self.driver)
        enter_text_for_element(self.driver, create_filesystem_page.filesystem_text, self.filesystem_name)
        create_filesystem_page.create_filesystem_button.click()
        wait_for_element(self.driver, create_filesystem_page.error_span, self.medium_wait)
        actual_message = create_filesystem_page.validation_error_message(1)
        self.assertEqual(validation_messages['mdt_not_selected'], actual_message, 'Error message for not selecting MDT is not displayed')

    def test_conf_params(self):
        """Test to check whether configuration params are set correctly"""

        self.driver.refresh()
        wait_for_element(self.driver, "#btnCreateFS", self.medium_wait)
        create_filesystem_page = CreateFilesystem(self.driver)

        # Click advanced button
        create_filesystem_page.advanced_button.click()

        # Set values for conf params
        for param in self.conf_params:
            self.test_logger.info('Setting value for param name:' + param + " value:" + self.conf_params[param])
            param_element_id = 'conf_param_' + param
            enter_text_for_element(self.driver, "input[id='" + param_element_id + "']", self.conf_params[param])

        # Click Apply button
        self.driver.find_element_by_css_selector(create_filesystem_page.conf_param_apply_button).click()

        # Check whether conf param dialog is closed
        self.assertFalse(element_visible(self.driver, create_filesystem_page.conf_param_apply_button), "Configuration dialog not closed")

        # Reopen the conf param dialog and check whether new conf param values are displayed correctly
        create_filesystem_page.advanced_button.click()
        for param in self.conf_params:
            self.test_logger.info('Check whether value: ' + self.conf_params[param] + ' for param name:' + param + ' is set correctly')
            param_element_id = 'conf_param_' + param
            self.assertEqual(self.driver.find_element_by_css_selector("input[id='" + param_element_id + "']").get_attribute("value"), self.conf_params[param], "New conf param values not displayed correctly")

    def test_invalid_conf_params(self):
        """Test to check whether invalid configuration params are validated"""

        self.navigation.go('Configure', 'Servers')
        wait_for_datatable(self.driver, '#server_configuration')
        self.server_page = Servers(self.driver)
        self.server_page.add_servers(self.host_list)

        self.navigation.go('Configure', 'MGTs')
        self.driver.refresh()
        wait_for_datatable(self.driver, '#mgt_configuration')
        self.mgt_page = Mgt(self.driver)
        self.mgt_page.create_mgt(self.mgt_host_name, self.mgt_device_node)

        self.navigation.go('Configure', 'Create_new_filesystem')
        wait_for_element(self.driver, "#btnCreateFS", self.medium_wait)
        self.driver.refresh()
        create_filesystem_page = CreateFilesystem(self.driver)

        enter_text_for_element(self.driver, create_filesystem_page.filesystem_text, self.filesystem_name)
        create_filesystem_page.select_mgt(self.mgt_host_name)
        create_filesystem_page.select_mdt(self.mdt_host_name, self.mdt_device_node)
        create_filesystem_page.select_ost(self.ost_host_name, self.ost_device_node)

        # Click advanced button
        create_filesystem_page.advanced_button.click()

        # Set values for conf params
        for param in self.conf_params:
            self.test_logger.info('Setting value for param name:' + param + " value:" + "non_numeric_value")
            param_element_id = 'conf_param_' + param
            self.driver.find_element_by_css_selector("input[id='" + param_element_id + "']").send_keys("non_numeric_value")

        # Click Apply button
        self.driver.find_element_by_css_selector(create_filesystem_page.conf_param_apply_button).click()
        create_filesystem_page.create_filesystem_button.click()

        wait_for_element(self.driver, create_filesystem_page.error_dialog, self.medium_wait)
        self.assertTrue(self.driver.find_element_by_css_selector(create_filesystem_page.error_dialog).text.__contains__(param), "No validation message for conf param " + param)

        self.driver.find_element_by_css_selector(create_filesystem_page.error_dialog_dismiss).click()

        self.navigation.go('Configure', 'MGTs')
        self.driver.refresh()
        wait_for_datatable(self.driver, '#mgt_configuration')
        mgt_page = Mgt(self.driver)
        mgt_page.transition(self.mgt_host_name, self.mgt_device_node, static_text['remove_mgt'])

        self.navigation.go('Configure', 'Servers')
        server_page = Servers(self.driver)
        wait_for_datatable(self.driver, '#server_configuration')
        server_page.remove_servers(self.host_list)

if __name__ == '__main__':
    django.utils.unittest.main()
