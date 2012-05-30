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
from views.create_filesystem import CreateFilesystem
from base import wait_for_screen_unblock


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
        self.mgt_host_name = self.host_list[0]['address']
        self.mgt_device_node = self.host_list[0]['device_node'][0]

        # Test data for conf params
        self.conf_param_test_data = self.test_data.get_test_data_for_conf_params()

        # Test data for file system
        self.fs_test_data = self.test_data.get_test_data_for_filesystem_configuration()
        self.filesystem_name = self.fs_test_data['name']
        self.mgt_name = self.host_list[0]['address']
        self.mdt_host_name = self.host_list[1]["address"]
        self.mdt_device_node = self.host_list[1]["device_node"][0]
        self.ost_host_name = self.host_list[1]["address"]
        self.ost_device_node = self.host_list[1]["device_node"][1]
        self.original_conf_params = self.conf_param_test_data['filesystem_conf_params']

        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.create_filesystem_with_server_and_mgt(self.host_list, self.mgt_host_name, self.mgt_device_node, self.filesystem_name, self.mgt_name, self.mdt_host_name, self.mdt_device_node, self.ost_host_name, self.ost_device_node, self.original_conf_params)

        # Test data for editing a file system
        self.conf_params = self.conf_param_test_data['edit_filesystem_conf_params']
        self.mdt_conf_params = self.conf_param_test_data['mdt_conf_params']
        self.ost_host_name = self.host_list[0]["address"]
        self.ost_device_node = self.host_list[0]["device_node"][1]
        self.ost_conf_params = self.conf_param_test_data['ost_conf_params']

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
        wait_for_screen_unblock(self.driver, wait_time['medium'])
        wait_for_datatable(self.driver, '#' + self.edit_filesystem_page.mdt_table)

        # Click advanced button
        self.driver.find_element_by_css_selector("div#filesystem_detail button.advanced").click()
        wait_for_element(self.driver, self.edit_filesystem_page.conf_param_apply_button, self.medium_wait)

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
        wait_for_screen_unblock(self.driver, wait_time['medium'])

        # Check whether conf params are set successfully and dialog is closed
        self.assertFalse(element_visible(self.driver, self.edit_filesystem_page.conf_param_apply_button), "Configuration dialog not closed")

        # Reopen the conf param dialog and check whether newly set conf param values are displayed correctly
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.advanced_button).click()
        for param in self.conf_params:
            param_element_id = 'conf_param_' + param
            self.assertEqual(self.driver.find_element_by_css_selector("input[id='" + param_element_id + "']").get_attribute("value"), self.conf_params[param], "New conf param values not displayed correctly after config dialog is reopened")

        # Reload page
        self.driver.refresh()
        wait_for_screen_unblock(self.driver, wait_time['medium'])
        wait_for_datatable(self.driver, '#' + self.edit_filesystem_page.mdt_table)

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
        wait_for_screen_unblock(self.driver, wait_time['medium'])
        wait_for_element(self.driver, self.edit_filesystem_page.advanced_button, self.medium_wait)

        # Click target element to open and set conf params
        self.edit_filesystem_page.open_conf_param(self.edit_filesystem_page.mdt_table, self.mdt_host_name, self.mdt_device_node)
        self.edit_filesystem_page.set_conf_params(self.mdt_conf_params)

        # Click Apply button
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.target_conf_param_apply_button).click()
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.popup_dialog_close_button).click()
        wait_for_screen_unblock(self.driver, wait_time['medium'])

        # Check whether conf params are set successfully and dialog is closed
        self.assertFalse(element_visible(self.driver, self.edit_filesystem_page.target_conf_param_apply_button), "Configuration dialog not closed")

        # Reopen the conf param dialog and check whether newly set conf param values are displayed correctly
        self.edit_filesystem_page.open_conf_param(self.edit_filesystem_page.mdt_table, self.mdt_host_name, self.mdt_device_node)
        self.edit_filesystem_page.check_conf_params(self.mdt_conf_params)
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.popup_dialog_close_button).click()
        wait_for_screen_unblock(self.driver, wait_time['medium'])

        # Reload page
        self.driver.refresh()
        wait_for_screen_unblock(self.driver, wait_time['medium'])
        wait_for_element(self.driver, self.edit_filesystem_page.advanced_button, self.medium_wait)

        # Again open the conf param dialog and check whether newly set conf param values are displayed correctly (after reloading the page)
        self.edit_filesystem_page.open_conf_param(self.edit_filesystem_page.mdt_table, self.mdt_host_name, self.mdt_device_node)
        self.edit_filesystem_page.check_conf_params(self.mdt_conf_params)
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.popup_dialog_close_button).click()
        wait_for_screen_unblock(self.driver, wait_time['medium'])

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
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.popup_dialog_close_button).click()
        wait_for_screen_unblock(self.driver, wait_time['medium'])

        # Check whether conf params are set successfully and dialog is closed
        self.assertFalse(element_visible(self.driver, self.edit_filesystem_page.target_conf_param_apply_button), "Configuration dialog not closed")

        # Reopen the conf param dialog and check whether newly set conf param values are displayed correctly
        self.edit_filesystem_page.open_conf_param(self.edit_filesystem_page.ost_table, self.ost_host_name, self.ost_device_node)
        self.edit_filesystem_page.check_conf_params(self.ost_conf_params)
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.popup_dialog_close_button).click()
        wait_for_screen_unblock(self.driver, wait_time['medium'])

        # Reload page
        self.driver.refresh()
        wait_for_screen_unblock(self.driver, wait_time['medium'])
        wait_for_element(self.driver, self.edit_filesystem_page.advanced_button, self.medium_wait)

        # Again open the conf param dialog and check whether newly set conf param values are displayed correctly (after reloading the page)
        self.edit_filesystem_page.open_conf_param(self.edit_filesystem_page.ost_table, self.ost_host_name, self.ost_device_node)
        self.edit_filesystem_page.check_conf_params(self.ost_conf_params)
        self.driver.find_element_by_css_selector(self.edit_filesystem_page.popup_dialog_close_button).click()
        wait_for_screen_unblock(self.driver, wait_time['medium'])

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

        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.remove_filesystem_with_server_and_mgt(self.filesystem_name, self.mgt_host_name, self.mgt_device_node, self.host_list)

        super(TestEditFileSystem, self).tearDown()

if __name__ == '__main__':
    django.utils.unittest.main()
