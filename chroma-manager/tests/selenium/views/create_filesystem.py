#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from selenium.webdriver.support.ui import Select
from tests.selenium.base_view import BaseView
from tests.selenium.utils.element import (
    enter_text_for_element, find_visible_element_by_css_selector,
    wait_for_element_by_css_selector
)


class CreateFilesystem(BaseView):
    """
    Page Object for file system creation
    """
    def __init__(self, driver):
        super(CreateFilesystem, self).__init__(driver)

        # Initialise elements on this page
        self.error_dialog = 'div.error_dialog'
        self.edit_fs_title = '#edit_fs_title'
        self.conf_param_apply_button = "button.conf_param_apply_button"
        self.error_span = "span.error"
        self.error_dialog_dismiss = "button.dismiss_button"

        self.mgt_existing_dropdown = self.driver.find_element_by_css_selector('#mgt_existing_dropdown')
        self.create_filesystem_button = self.driver.find_element_by_css_selector('#btnCreateFS')
        self.advanced_button = self.driver.find_element_by_css_selector("button.advanced")
        self.volume_chooser_selected = self.driver.find_elements_by_class_name("volume_chooser_selected")

    def select_mgt(self, mgt_name):
        """Select an MGT from MGT chooser"""
        mgt_list = Select(self.mgt_existing_dropdown)
        mgt_list.select_by_visible_text(mgt_name)

    def select_mgt_volume(self, server_address, volume_name):
        self.volume_chooser_open_and_select('mgt_chooser', server_address, volume_name)

    def select_mdt_volume(self, server_address, volume_name):
        """Select an MDT from MDT chooser"""
        self.volume_chooser_open_and_select('mdt_chooser', server_address, volume_name)

    def select_ost_volume(self, server_address, volume_name):
        """Select an OST from OST chooser"""
        self.volume_chooser_select('ost_chooser', server_address, volume_name, multi = True)

    def enter_name(self, filesystem_name):
        enter_text_for_element(self.driver, "#txtfsnameid", filesystem_name)

    def validation_error_message(self, index):
        # Index: 0 - FS, 1 - MGT, 2 - MDT
        """Returns error message displayed in error dialog box"""
        self.error_message = self.driver.find_elements_by_css_selector(self.error_span)
        return self.error_message[index].text

    def open_conf_params(self):
        self.advanced_button.click()
        wait_for_element_by_css_selector(self.driver, self.conf_param_apply_button, self.standard_wait)

    def close_conf_params(self):
        self.driver.find_element_by_css_selector(self.conf_param_apply_button).click()

    @property
    def conf_params_open(self):
        return bool(find_visible_element_by_css_selector(self.driver, self.conf_param_apply_button))

    @property
    def name_error(self):
        """Validation error text for filesystem name entry if present"""
        return self.get_input_error(self.driver.find_element_by_css_selector('#txtfsnameid'))

    @property
    def mgt_volume_error(self):
        """Validation error text for MGT volume chooser if present"""
        return self.get_input_error(self.driver.find_element_by_css_selector('button#mgt_chooser'))

    @property
    def mdt_volume_error(self):
        """Validation error text for MDT volume chooser if present"""
        return self.get_input_error(self.driver.find_element_by_css_selector('button#mdt_chooser'))

    @property
    def mdt_inode_size_error(self):
        return self.get_input_error(self.driver.find_element_by_css_selector('#inode_size'))

    @property
    def mdt_bytes_per_inode_error(self):
        return self.get_input_error(self.driver.find_element_by_css_selector('#bytes_per_inode'))

    def expand_mdt_advanced(self):
        if not self.mdt_advanced_visible:
            self.driver.find_element_by_css_selector("label[for='mdt_advanced_button']").click()

    def enter_mdt_inode_size(self, text):
        enter_text_for_element(self.driver, "#inode_size", text)

    def enter_mdt_bytes_per_inode(self, text):
        enter_text_for_element(self.driver, "#bytes_per_inode", text)

    def collapse_mdt_advanced(self):
        if self.mdt_advanced_visible:
            self.driver.find_element_by_css_selector("label[for='mdt_advanced_button']").click()

    @property
    def mdt_advanced_visible(self):
        return bool(find_visible_element_by_css_selector(self.driver, '#mdt_advanced'))
