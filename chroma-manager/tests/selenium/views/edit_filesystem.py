#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import logging
from base import enter_text_for_element
from base import wait_for_datatable
from base import wait_for_transition
from utils.constants import wait_time
from selenium.webdriver.support.ui import WebDriverWait


class EditFilesystem:
    """
    Page Object for editing file system
    """
    def __init__(self, driver):
        self.driver = driver

        self.long_wait = wait_time['long']
        self.medium_wait = wait_time['medium']

        # Initialise elements on this page
        self.advanced_button = "div#filesystem_detail button.advanced"
        self.conf_param_apply_button = "button.conf_param_apply_button"
        # Conf param apply button on pop-up dialog for MDT and OST
        self.target_conf_param_apply_button = "#ConfigParam_Apply"
        self.popup_container = "#popup_container"
        self.popup_message = "#popup_message"
        self.popup_ok = "#popup_ok"
        self.mdt_table = "mdt"
        self.ost_table = "ost"
        self.ost_data_table = "ost_content"
        self.mdt_data_table = "mdt_content"
        self.mgt_data_table = "example_content"

        self.config_param_tab = ""

        self.test_logger = logging.getLogger(__name__)
        self.test_logger.addHandler(logging.StreamHandler())
        self.test_logger.setLevel(logging.INFO)

    def open_conf_param(self, target_datatable, host_name, device_node):
        """Open conf param dialog for target element"""

        datatable_rows_list = self.driver.find_elements_by_xpath("id('" + target_datatable + "')/tbody/tr")
        for tr in datatable_rows_list:
            if tr.find_element_by_xpath("td[2]").text == device_node and tr.find_element_by_xpath("td[3]").text == host_name:
                tr.find_element_by_xpath("td[1]/a").click()
                self.config_param_tab = self.driver.find_element_by_xpath("id('target_dialog_tabs')/ul/li[3]/a")
                self.config_param_tab.click()

    def set_conf_params(self, target_conf_params):
        # Set new conf param values for target
        for param in target_conf_params:
            self.test_logger.info('Setting value for param name:' + param + " value:" + target_conf_params[param])
            param_element_id = 'conf_param_' + param
            enter_text_for_element(self.driver, "input[id='" + param_element_id + "']", target_conf_params[param])

    def check_conf_params(self, target_conf_params):
        for param in target_conf_params:
            param_element_id = 'conf_param_' + param
            if self.driver.find_element_by_css_selector("input[id='" + param_element_id + "']").get_attribute("value") != target_conf_params[param]:
                raise RuntimeError("Conf params not set correctly")

    def select_ost(self, host_name, device_node):
        """Click button to add new OST and select an OST/s from ost chooser"""
        WebDriverWait(self.driver, self.medium_wait).until(lambda driver: self.driver.find_element_by_css_selector("#btnNewOST").is_displayed())
        self.driver.find_element_by_css_selector('#btnNewOST').click()

        ost_rows = self.driver.find_elements_by_xpath("id('new_ost_chooser_table')/tbody/tr")
        for tr in ost_rows:
            if tr.find_element_by_xpath("td[6]").text == host_name and tr.find_element_by_xpath("td[2]").text == device_node:
                tr.click()
                self.driver.find_element_by_css_selector('#ost_ok_button').click()
                return

        raise RuntimeError("Cannot choose OST with hostname: " + host_name + " and device node " + device_node + " from list")

    def locate_target(self, data_table, primary_server_name, volume_name):
        """Locate target by volume / primary server from list and return the complete row"""
        wait_for_datatable(self.driver, '#ost')

        target_list = self.driver.find_elements_by_xpath("id('" + data_table + "')/tr")
        for tr in target_list:
            if primary_server_name != '' and volume_name != '':
                if tr.find_element_by_xpath("td[3]").text == primary_server_name and tr.find_element_by_xpath("td[2]").text == volume_name:
                    return tr

        raise RuntimeError("Target with primary server: " + primary_server_name + " and volume:" + volume_name + " not found in " + data_table + " list")

    def transition_target(self, data_table, host_name, device_node, transition_name, transition_confirm = True):
        """Perform given transition on target"""

        target_host_row = self.locate_target(data_table, host_name, device_node)
        buttons = target_host_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == transition_name:
                button.click()
                if transition_confirm:
                    WebDriverWait(self.driver, self.medium_wait).until(lambda driver: self.driver.find_element_by_css_selector("#transition_confirm_button").is_displayed())
                    self.driver.find_element_by_css_selector('#transition_confirm_button').click()
                wait_for_transition(self.driver, self.long_wait)
                return

        raise RuntimeError("Cannot perform transition " + transition_name + " on " + data_table + " for Volume " + device_node + " and server " + host_name)

    def check_action_available_for_target(self, data_table, host_name, device_node, action_name):
        """Check whether the given transition(action) is present in all possible transitions available for target"""

        is_compared = False
        target_ost_row = self.locate_target(data_table, host_name, device_node)
        buttons = target_ost_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == action_name:
                is_compared = True

        return is_compared
