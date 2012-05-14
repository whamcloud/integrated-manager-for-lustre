#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import django.utils.unittest
from views.filesystem import Filesystem
from views.edit_filesystem import EditFilesystem
from base import SeleniumBaseTestCase
from utils.sample_data import Testdata
from base import wait_for_datatable
from selenium.webdriver.support.ui import WebDriverWait
from utils.constants import wait_time
from base import wait_for_element
from base import element_visible
from views.mgt import Mgt
from views.servers import Servers
from views.create_filesystem import CreateFilesystem
from utils.constants import static_text


class TestEditFileSystem(SeleniumBaseTestCase):
    """Test cases for editing file system"""

    def setUp(self):
        super(TestEditFileSystem, self).setUp()
        self.standard_wait = wait_time['standard']
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
        self.original_conf_params = self.fs_test_data[0]['conf_params']

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
        create_filesystem_page.create(self.filesystem_name, self.mgt_name, self.mdt_host_name, self.mdt_device_node, self.ost_host_name, self.ost_device_node, self.original_conf_params)

        # Test data for editing a file system
        self.fs_edit_test_data = self.test_data.get_test_data_for_editing_filesystem()
        self.conf_params = self.fs_edit_test_data[0]['conf_params']
        self.mdt_conf_params = self.fs_edit_test_data[0]['mdt']['conf_params']
        self.ost_host_name = self.fs_edit_test_data[0]['osts'][0]['mounts'][0]['host']
        self.ost_device_node = self.fs_edit_test_data[0]['osts'][0]['mounts'][0]['device_node']
        self.ost_conf_params = self.fs_edit_test_data[0]['osts'][0]['mounts'][0]['conf_params']

        self.navigation.go('Configure')
        self.driver.refresh()
        wait_for_datatable(self.driver, '#fs_list')
        self.fs_page = Filesystem(self.driver)
        self.fs_page.edit(self.filesystem_name)

    def test_conf_params_for_filesystem(self):
        """
        Test scenarios for file system conf params
        Test that a conf param can be set
        Test that if the dialog is re-opened the new conf param value is displayed correctly
        Test that if the page is reloaded the new conf param value is displayed correctly
        """
        self.edit_filesystem_page = EditFilesystem(self.driver)
        wait_for_datatable(self.driver, '#' + self.edit_filesystem_page.mdt_table)

        # Click advanced button
        self.driver.find_element_by_css_selector("div#filesystem_detail button.advanced").click()

        # Check whether conf param values set during file system creation are displayed correctly
        for param in self.original_conf_params:
            self.test_logger.info('Checking param name:' + param + " value:" + self.original_conf_params[param])
            param_element_id = 'conf_param_' + param
            wait_for_element(self.driver, "input[id='" + param_element_id + "']", self.medium_wait)
            self.assertEqual(self.driver.find_element_by_css_selector("input[id='" + param_element_id + "']").get_attribute("value"), self.original_conf_params[param], "New conf param values not displayed correctly")

        # Set new values for conf params
        self.edit_filesystem_page.set_conf_params(self.conf_params)

        # Click Apply button
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.conf_param_apply_button).click()
        wait_for_element(self.driver, self.edit_filesystem_page.popup_container, self.medium_wait)

        # Check whether conf params are set successfully and dialog is closed
        self.assertEqual(self.driver.find_element_by_css_selector(self.edit_filesystem_page.popup_message).text, "Update Successful", "Error in updating the conf params for file system")
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.popup_ok).click()
        self.assertFalse(element_visible(self.driver, self.edit_filesystem_page.conf_param_apply_button), "Configuration dialog not closed")

        # Reopen the conf param dialog and check whether newly set conf param values are displayed correctly
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.advanced_button).click()
        for param in self.conf_params:
            param_element_id = 'conf_param_' + param
            self.assertEqual(self.driver.find_element_by_css_selector("input[id='" + param_element_id + "']").get_attribute("value"), self.conf_params[param], "New conf param values not displayed correctly after config dialog is reopened")

        # Reload page
        self.driver.refresh()

        # Again open the conf param dialog and check whether newly set conf param values are displayed correctly (after reloading the page)
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.advanced_button).click()
        for param in self.conf_params:
            param_element_id = 'conf_param_' + param
            self.assertEqual(self.driver.find_element_by_css_selector("input[id='" + param_element_id + "']").get_attribute("value"), self.conf_params[param], "New conf param values not displayed correctly after reloading page")

    def test_conf_params_for_mdt(self):
        """
        Test scenarios for setting MDT conf params
        """
        self.edit_filesystem_page = EditFilesystem(self.driver)
        wait_for_element(self.driver, self.edit_filesystem_page.advanced_button, self.medium_wait)

        # Click target element to open and set conf params
        self.edit_filesystem_page.open_conf_param(self.edit_filesystem_page.mdt_table, self.mdt_host_name, self.mdt_device_node)
        self.edit_filesystem_page.set_conf_params(self.mdt_conf_params)

        # Click Apply button
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.target_conf_param_apply_button).click()
        wait_for_element(self.driver, self.edit_filesystem_page.popup_container, self.medium_wait)

        # Check whether conf params are set successfully and dialog is closed
        self.assertEqual(self.driver.find_element_by_css_selector(self.edit_filesystem_page.popup_message).text, "Update Successful", "Error in setting the conf params for file system")
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.popup_ok).click()
        self.assertFalse(element_visible(self.driver, self.edit_filesystem_page.target_conf_param_apply_button), "Configuration dialog not closed")

        # Reopen the conf param dialog and check whether newly set conf param values are displayed correctly
        self.edit_filesystem_page.open_conf_param(self.edit_filesystem_page.mdt_table, self.mdt_host_name, self.mdt_device_node)
        self.edit_filesystem_page.check_conf_params(self.mdt_conf_params)

        # Reload page
        self.driver.refresh()
        wait_for_element(self.driver, self.edit_filesystem_page.advanced_button, self.medium_wait)

        # Again open the conf param dialog and check whether newly set conf param values are displayed correctly (after reloading the page)
        self.edit_filesystem_page.open_conf_param(self.edit_filesystem_page.mdt_table, self.mdt_host_name, self.mdt_device_node)
        self.edit_filesystem_page.check_conf_params(self.mdt_conf_params)

    def test_conf_params_for_ost(self):
        """
        Test scenarios for setting OST conf params
        """
        self.add_ost()

        self.edit_filesystem_page = EditFilesystem(self.driver)
        wait_for_element(self.driver, self.edit_filesystem_page.advanced_button, self.medium_wait)

        # Click target element to open and set conf params
        self.edit_filesystem_page.open_conf_param(self.edit_filesystem_page.ost_table, self.ost_host_name, self.ost_device_node)
        self.edit_filesystem_page.set_conf_params(self.ost_conf_params)

        # Click Apply button
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.target_conf_param_apply_button).click()
        wait_for_element(self.driver, self.edit_filesystem_page.popup_container, self.medium_wait)

        # Check whether conf params are set successfully and dialog is closed
        self.assertEqual(self.driver.find_element_by_css_selector(self.edit_filesystem_page.popup_message).text, "Update Successful", "Error in setting the conf params for file system")
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.popup_ok).click()
        self.assertFalse(element_visible(self.driver, self.edit_filesystem_page.target_conf_param_apply_button), "Configuration dialog not closed")

        # Reopen the conf param dialog and check whether newly set conf param values are displayed correctly
        self.edit_filesystem_page.open_conf_param(self.edit_filesystem_page.ost_table, self.ost_host_name, self.ost_device_node)
        self.edit_filesystem_page.check_conf_params(self.ost_conf_params)

        # Reload page
        self.driver.refresh()
        wait_for_element(self.driver, self.edit_filesystem_page.advanced_button, self.medium_wait)

        # Again open the conf param dialog and check whether newly set conf param values are displayed correctly (after reloading the page)
        self.edit_filesystem_page.open_conf_param(self.edit_filesystem_page.ost_table, self.ost_host_name, self.ost_device_node)
        self.edit_filesystem_page.check_conf_params(self.ost_conf_params)

    def test_add_ost(self):
        """Test for adding OST"""

        self.add_ost()

    def test_start_and_stop_ost(self):
        """Test for starting and stopping OST"""

        self.add_ost()
        self.stop_ost()
        self.driver.refresh()
        wait_for_element(self.driver, self.edit_filesystem_page.advanced_button, self.medium_wait)
        self.edit_filesystem_page = EditFilesystem(self.driver)
        self.start_ost()

    def test_remove_ost(self):
        """Test for removing OST"""

        self.add_ost()
        self.driver.refresh()
        wait_for_element(self.driver, self.edit_filesystem_page.advanced_button, self.medium_wait)
        self.edit_filesystem_page = EditFilesystem(self.driver)
        self.stop_ost()
        self.driver.refresh()
        wait_for_element(self.driver, self.edit_filesystem_page.advanced_button, self.medium_wait)
        self.edit_filesystem_page = EditFilesystem(self.driver)
        self.remove_ost()

    def test_start_and_stop_mdt(self):
        """Test for starting and stopping MDT"""

        self.stop_mdt()
        self.driver.refresh()
        wait_for_element(self.driver, self.edit_filesystem_page.advanced_button, self.medium_wait)
        self.fs_page = Filesystem(self.driver)
        self.start_mdt()

    def test_start_and_stop_mgt(self):
        """Test for starting and stopping MGT"""

        self.stop_mgt()
        self.driver.refresh()
        wait_for_element(self.driver, self.edit_filesystem_page.advanced_button, self.medium_wait)
        self.fs_page = Filesystem(self.driver)
        self.start_mgt()

    def add_ost(self):
        self.edit_filesystem_page = EditFilesystem(self.driver)
        self.edit_filesystem_page.select_ost(self.ost_host_name, self.ost_device_node)

        WebDriverWait(self.driver, self.standard_wait).until(lambda driver: self.driver.find_element_by_css_selector("img.notification_icon").is_displayed())
        WebDriverWait(self.driver, self.standard_wait).until(lambda driver: self.driver.find_element_by_css_selector("img.notification_icon").is_displayed() == False)
        self.edit_filesystem_page.locate_target(self.edit_filesystem_page.ost_data_table, self.ost_host_name, self.ost_device_node)

    def stop_ost(self):
        self.edit_filesystem_page = EditFilesystem(self.driver)
        self.edit_filesystem_page.transition_target(self.edit_filesystem_page.ost_data_table, self.ost_host_name, self.ost_device_node, 'Stop')
        self.assertFalse(self.edit_filesystem_page.check_action_available_for_target(self.edit_filesystem_page.ost_data_table, self.ost_host_name, self.ost_device_node, 'Stop'))

    def start_ost(self):
        self.edit_filesystem_page = EditFilesystem(self.driver)
        self.edit_filesystem_page.transition_target(self.edit_filesystem_page.ost_data_table, self.ost_host_name, self.ost_device_node, 'Start', False)
        self.assertFalse(self.edit_filesystem_page.check_action_available_for_target(self.edit_filesystem_page.ost_data_table, self.ost_host_name, self.ost_device_node, 'Start'))

    def remove_ost(self):
        self.edit_filesystem_page = EditFilesystem(self.driver)
        self.edit_filesystem_page.transition_target(self.edit_filesystem_page.ost_data_table, self.ost_host_name, self.ost_device_node, 'Remove')
        self.assertFalse(self.edit_filesystem_page.check_action_available_for_target(self.edit_filesystem_page.ost_data_table, self.ost_host_name, self.ost_device_node, 'Remove'))

    def stop_mdt(self):
        self.edit_filesystem_page = EditFilesystem(self.driver)
        self.edit_filesystem_page.transition_target(self.edit_filesystem_page.mdt_data_table, self.mdt_host_name, self.mdt_device_node, 'Stop')
        self.assertFalse(self.edit_filesystem_page.check_action_available_for_target(self.edit_filesystem_page.mdt_data_table, self.mdt_host_name, self.mdt_device_node, 'Stop'))

    def start_mdt(self):
        self.edit_filesystem_page = EditFilesystem(self.driver)
        self.edit_filesystem_page.transition_target(self.edit_filesystem_page.mdt_data_table, self.mdt_host_name, self.mdt_device_node, 'Start', False)
        self.assertFalse(self.edit_filesystem_page.check_action_available_for_target(self.edit_filesystem_page.mdt_data_table, self.mdt_host_name, self.mdt_device_node, 'Start'))

    def stop_mgt(self):
        self.edit_filesystem_page = EditFilesystem(self.driver)
        self.edit_filesystem_page.transition_target(self.edit_filesystem_page.mgt_data_table, self.mgt_host_name, self.mgt_device_node, 'Stop')
        self.assertFalse(self.edit_filesystem_page.check_action_available_for_target(self.edit_filesystem_page.mgt_data_table, self.mgt_host_name, self.mgt_device_node, 'Stop'))

    def start_mgt(self):
        self.edit_filesystem_page = EditFilesystem(self.driver)
        self.edit_filesystem_page.transition_target(self.edit_filesystem_page.mgt_data_table, self.mgt_host_name, self.mgt_device_node, 'Start', False)
        self.assertFalse(self.edit_filesystem_page.check_action_available_for_target(self.edit_filesystem_page.mgt_data_table, self.mgt_host_name, self.mgt_device_node, 'Start'))

    def tearDown(self):
        self.driver.refresh()

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
