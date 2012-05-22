#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import logging
from selenium.webdriver.support.ui import Select
from base import enter_text_for_element
from base import wait_for_element
from base import wait_for_transition
from utils.constants import wait_time
from utils.navigation import Navigation
from base import wait_for_datatable
from views.mgt import Mgt
from views.servers import Servers
from views.filesystem import Filesystem
from utils.constants import static_text


class CreateFilesystem:
    """
    Page Object for file system creation
    """
    def __init__(self, driver):
        self.driver = driver

        self.medium_wait = wait_time['medium']

        # Initialise elements on this page
        self.filesystem_text = '#txtfsnameid'
        self.mgt_chooser = '#mgt_chooser'
        self.mdt_chooser = '#mdt_chooser'
        self.ost_chooser = '#ost_chooser'
        self.error_dialog = 'div.error_dialog'
        self.edit_fs_title = '#edit_fs_title'
        self.conf_param_apply_button = "button.conf_param_apply_button"
        self.error_span = "span.error"
        self.error_dialog_dismiss = "button.dismiss_button"

        self.mgt_existing_dropdown = self.driver.find_element_by_css_selector('#mgt_existing_dropdown')
        self.create_filesystem_button = self.driver.find_element_by_css_selector('#btnCreateFS')
        self.advanced_button = self.driver.find_element_by_css_selector("button.advanced")
        self.volume_chooser_selected = self.driver.find_elements_by_class_name("volume_chooser_selected")

        self.test_logger = logging.getLogger(__name__)
        self.test_logger.addHandler(logging.StreamHandler())
        self.test_logger.setLevel(logging.INFO)

    def select_mgt(self, mgt_name):
        """Select an MGT from MGT chooser"""
        mgt_list = Select(self.mgt_existing_dropdown)
        mgt_list.select_by_visible_text(mgt_name)

    def select_mdt(self, host_name, device_node):
        """Select an MDT from MDT chooser"""
        mdtchooser = self.driver.find_elements_by_class_name("volume_chooser_selected").__getitem__(1)
        mdtchooser.click()
        mdt_rows = self.driver.find_elements_by_xpath("id('mdt_chooser_table')/tbody/tr")
        for tr in mdt_rows:
            if tr.find_element_by_xpath("td[5]").text == host_name and tr.find_element_by_xpath("td[1]").text == device_node:
                tr.click()
                return

        raise RuntimeError("MDT with host_name " + host_name + " and device node " + device_node + " not found")

    def select_ost(self, host_name, device_node):
        """Select an OST/s from OST chooser"""
        ost_rows = self.driver.find_elements_by_xpath("id('ost_chooser_table')/tbody/tr")
        for tr in ost_rows:
            if tr.find_element_by_xpath("td[6]").text == host_name and tr.find_element_by_xpath("td[2]").text == device_node:
                tr.click()
                return

        raise RuntimeError("OST with host_name " + host_name + " and device node " + device_node + " not found")

    def validation_error_message(self, index):
        # Index: 0 - FS, 1 - MGT, 2 - MDT
        """Returns error message displayed in error dialog box"""
        self.error_message = self.driver.find_elements_by_css_selector(self.error_span)
        return self.error_message[index].text

    def verify_created_filesystem(self, filesystem_name, mgt_name, mdt_host_name, mdt_device_node, ost_host_name, ost_device_node):
        """Checks whether MGT, MDT and OST are associated with file system"""
        create_message = ''

        if self.driver.find_element_by_css_selector(self.edit_fs_title).text != 'File System ' + filesystem_name:
            create_message = create_message + 'File system not created successfully'

        mgt_rows = self.driver.find_elements_by_xpath("id('example_content')/tr[2]")
        for tr in mgt_rows:
            if tr.find_element_by_xpath("td[3]").text != mgt_name:
                create_message = create_message + "MGS " + mgt_name + " is not associated with filesystem"

        mdt_rows = self.driver.find_elements_by_xpath("id('mdt_content')/tr[2]")
        for tr in mdt_rows:
            if tr.find_element_by_xpath("td[3]").text != mdt_host_name or tr.find_element_by_xpath("td[2]").text != mdt_device_node:
                create_message = create_message + "MDT " + mdt_host_name + " is not associated with filesystem"

        ost_rows = self.driver.find_elements_by_xpath("id('ost_content')/tr[2]")
        for tr in ost_rows:
            if tr.find_element_by_xpath("td[3]").text != ost_host_name or tr.find_element_by_xpath("td[2]").text != ost_device_node:
                create_message = create_message + "OST " + ost_host_name + " is not associated with filesystem"

        return create_message

    def create(self, filesystem_name, mgt_name, mdt_host_name, mdt_device_node, ost_host_name, ost_device_node, conf_params):
        """Enters all data required to create a filesystem"""
        wait_for_element(self.driver, "#btnCreateFS", self.medium_wait)

        enter_text_for_element(self.driver, self.filesystem_text, filesystem_name)

        # Set config params
        self.advanced_button.click()
        for param in conf_params:
            self.test_logger.info('Setting value for param name:' + param + " value:" + conf_params[param])
            param_element_id = 'conf_param_' + param
            wait_for_element(self.driver, "input[id='" + param_element_id + "']", self.medium_wait)
            enter_text_for_element(self.driver, "input[id='" + param_element_id + "']", conf_params[param])

        self.driver.find_element_by_css_selector(self.conf_param_apply_button).click()

        self.select_mgt(mgt_name)
        self.select_mdt(mdt_host_name, mdt_device_node)
        self.select_ost(ost_host_name, ost_device_node)
        self.create_filesystem_button.click()

        wait_for_element(self.driver, self.edit_fs_title, self.medium_wait)
        wait_for_transition(self.driver, 300)

    def create_filesystem_with_server_and_mgt(self, host_list, mgt_host_name, mgt_device_node, filesystem_name, mgt_name, mdt_host_name, mdt_device_node, ost_host_name, ost_device_node, conf_params):
        self.navigation = Navigation(self.driver)

        self.navigation.go('Configure', 'Servers')
        wait_for_datatable(self.driver, '#server_configuration')
        self.server_page = Servers(self.driver)
        self.server_page.add_servers(host_list)

        self.navigation.go('Configure', 'MGTs')
        self.driver.refresh()
        wait_for_element(self.driver, 'span.volume_chooser_selected', self.medium_wait)
        self.mgt_page = Mgt(self.driver)
        self.mgt_page.create_mgt(mgt_host_name, mgt_device_node)

        self.navigation.go('Configure', 'Create_new_filesystem')
        self.driver.refresh()
        wait_for_element(self.driver, "#btnCreateFS", self.medium_wait)
        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.create(filesystem_name, mgt_name, mdt_host_name, mdt_device_node, ost_host_name, ost_device_node, conf_params)

    def remove_filesystem_with_server_and_mgt(self, filesystem_name, mgt_host_name, mgt_device_node, host_list):
        self.navigation = Navigation(self.driver)

        self.navigation.go('Configure')
        fs_page = Filesystem(self.driver)
        wait_for_datatable(self.driver, '#fs_list')
        fs_page.transition(filesystem_name, static_text['remove_fs'])

        self.navigation.go('Configure', 'MGTs')
        self.driver.refresh()
        wait_for_element(self.driver, 'span.volume_chooser_selected', self.medium_wait)
        mgt_page = Mgt(self.driver)
        mgt_page.transition(mgt_host_name, mgt_device_node, static_text['remove_mgt'])

        self.navigation.go('Configure', 'Servers')
        self.driver.refresh()
        wait_for_datatable(self.driver, '#server_configuration')
        server_page = Servers(self.driver)
        server_page.remove_servers(host_list)
