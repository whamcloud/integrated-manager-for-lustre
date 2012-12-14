#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================

from selenium.common.exceptions import (
    NoSuchElementException, StaleElementReferenceException
)
from selenium.webdriver.support.ui import WebDriverWait

from tests.selenium.base import wait_for_transition
from tests.selenium.base_view import BaseView
from tests.selenium.utils.element import (
    find_visible_element_by_css_selector, wait_for_any_element_by_css_selector
)


class EditFilesystem(BaseView):
    """
    Page Object for editing file system
    """
    def __init__(self, driver):
        super(EditFilesystem, self).__init__(driver)

        # Initialise elements on this page
        self.advanced_button = "div#filesystem_detail button.advanced"
        self.conf_param_apply_button = "button.conf_param_apply_button"
        self.conf_param_close_button = "button.conf_param_close_button"
        # Conf param apply button on pop-up dialog for MDT and OST
        self.target_conf_param_apply_button = "button.conf_param_apply"
        self.popup_container = "#popup_container"
        self.popup_message = "#popup_message"
        self.popup_ok = "#popup_ok"
        self.mdt_table = "mdt"
        self.ost_table = "ost"
        self.ost_data_table = "ost_content"
        self.mdt_data_table = "mdt_content"
        self.mgt_data_table = "example_content"
        self.popup_dialog_close_button = "button.close"

        self.config_param_tab = ""

    def set_state(self, state):
        button_box = self.driver.find_element_by_css_selector('td#fs_actions')
        self.click_command_button(button_box, state)
        self.quiesce()

    def open_target_conf_params(self, target_name):
        link = WebDriverWait(self.driver, self.standard_wait).until(lambda driver: driver.find_element_by_link_text(target_name))
        link.click()
        self.quiesce()
        self.config_param_tab = self.driver.find_element_by_css_selector('div.target_detail a[href="#target_dialog_config_param_tab"]')
        self.config_param_tab.click()

    def apply_conf_params(self):
        """Given that a conf param dialog is visible, click its apply button"""
        self.get_visible_element_by_css_selector(self.conf_param_apply_button).click()
        self.quiesce()

    def close_conf_params(self):
        """Given that a conf param dialog is visible, click its apply button"""
        self.get_visible_element_by_css_selector(self.conf_param_close_button).click()

    def apply_target_conf_params(self):
        """Given that a target detail dialog is visible, and on the conf params tab click its apply button"""
        self.get_visible_element_by_css_selector("div.target_detail button.conf_param_apply").click()
        self.quiesce()

    def close_target_conf_params(self):
        """Given that a target detail dialog is visible, and on the conf params tab click its apply button"""
        self.get_visible_element_by_css_selector("div.ui-dialog-buttonset button.close").click()
        # Closing the dialog is a history.back() operation so wait for the reload
        self.quiesce()

    def conf_param_dialog_visible(self):
        element = find_visible_element_by_css_selector(self.driver, self.conf_param_apply_button)
        return bool(element)

    def open_fs_conf_param_dialog(self):
        self.driver.find_element_by_css_selector("div#filesystem_detail button.advanced").click()
        wait_for_any_element_by_css_selector(self.driver, self.conf_param_apply_button, self.medium_wait)

    def add_ost(self, primary_server_address, volume_name):
        """Click button to add new OST and select an OST/s from ost chooser"""
        # Open the ost chooser pop-up
        self.driver.find_element_by_css_selector('#btnNewOST').click()
        wait_for_any_element_by_css_selector(self.driver, '#new_ost_chooser_table', self.medium_wait)

        # Click on the row that has the given volume name and primary server address
        try:
            self.volume_chooser_select('new_ost_chooser', primary_server_address, volume_name, True)
        except (StaleElementReferenceException, NoSuchElementException):
            # Hate doing this, but volume chooser could be reloaded right in the middle of this action,
            # and havent found a good way to detect this, so if it fails in a specific way, we try again.
            self.volume_chooser_select('new_ost_chooser', primary_server_address, volume_name, True)

        # Submit and wait for the add to complete
        self.driver.find_element_by_css_selector('#ost_ok_button').click()
        self.quiesce()
        wait_for_transition(self.driver, self.long_wait)

    def ost_set_state(self, target_name, state):
        return self._target_set_state('ost', target_name, state)

    def mdt_set_state(self, target_name, state):
        return self._target_set_state('mdt', target_name, state)

    def mgt_set_state(self, target_name, state):
        return self._target_set_state('mgt_configuration_view', target_name, state)

    def _target_set_state(self, table_id, target_name, state):
        self.log.info("Setting state %s on target %s in %s" % (state, target_name, table_id))
        row = self.find_row_by_column_text(
            self.driver.find_element_by_css_selector('table#%s' % table_id),
                {0: target_name})
        self.click_command_button(row, state)

    @property
    def filesystem_name(self):
        return self.driver.find_element_by_css_selector('span#fs_name').text

    def _get_target_volumes(self, table_id):
        return self.get_table_text(
            self.driver.find_element_by_css_selector("#%s" % table_id),
            [1, 2]
        )

    @property
    def mgt_volumes(self):
        return self._get_target_volumes('mgt_configuration_view')

    @property
    def mdt_volumes(self):
        return self._get_target_volumes('mdt')

    @property
    def ost_volumes(self):
        return self._get_target_volumes('ost')

    @property
    def visible(self):
        return find_visible_element_by_css_selector(self.driver, 'div#filesystem-tab-detail')
