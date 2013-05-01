#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================
from selenium.common.exceptions import NoSuchElementException

from tests.selenium.base import wait_for_transition
from tests.selenium.base_view import DatatableView
from tests.selenium.utils.constants import static_text
from tests.selenium.utils.element import (
    enter_text_for_element, find_visible_element_by_css_selector
)


class Servers(DatatableView):
    """
    Page Object for server operations
    """
    def __init__(self, driver):
        super(Servers, self).__init__(driver)

        # Initialise elements on this page
        self.new_add_server_button = self.driver.find_element_by_css_selector('#btnAddNewHost')
        self.host_continue_button = 'a.add_host_submit_button'
        self.add_host_confirm_button = 'a.add_host_confirm_button'
        self.add_host_close_button = '#ssh_tab a.add_host_close_button'
        self.add_host_add_another_button = 'a.add_host_back_button'

        self.add_dialog_div = '#add_host_dialog'
        self.prompt_dialog_div = '#add_host_prompt'
        self.loading_dialog_div = 'div.add_host_loading'
        self.confirm_dialog_div = 'div.add_host_confirm'
        self.complete_dialog_div = 'div.add_host_complete'
        self.error_dialog_div = '#add_host_error'
        self.host_address_text = 'input.add_host_address'
        self.datatable_id = 'server_configuration'
        self.host_name_td = 0
        self.lnet_state_td = 1

    def open_detect_prompt(self):
        self.driver.find_element_by_css_selector('#server_list button.detect_button').click()
        self.quiesce()

    @property
    def host_selection_list_visible(self):
        return find_visible_element_by_css_selector(self.driver, 'div.host_selection_list')

    @property
    def host_selection_list_selected(self):
        """Return a dict of fqdn to bool"""
        result = {}
        for item in self.driver.find_elements_by_css_selector("ul.host_selection_list li"):
            result[item.text] = item.find_element_by_css_selector('input').is_selected()
        return result

    @property
    def host_selection_run_sensitive(self):
        return self.driver.find_element_by_css_selector('button.host_selection_run').is_enabled()

    def host_selection_run(self):
        self.driver.find_element_by_css_selector('button.host_selection_run').click()
        self.quiesce()

    def host_selection_list_all(self):
        self.driver.find_element_by_css_selector('a.select_all').click()

    def host_selection_list_none(self):
        self.driver.find_element_by_css_selector('a.select_none').click()

    def verify_added_server(self, host_name):
        """Returns whether newly added server is listed or not"""
        self.get_host_row(host_name)
        return True

    def server_visible(self, hostname):
        try:
            self.get_host_row(hostname)
            return True
        except NoSuchElementException:
            return False

    def get_server_list(self):
        """Returns server list"""
        # Get actual display text from list of webelement objects, append the names to a new list and sort the new list
        filtered_server_list = []
        for tr in self.rows:
            tds = tr.find_elements_by_tag_name("td")
            filtered_server_list.append(tds[self.host_name_td].text)
        filtered_server_list.sort()
        return filtered_server_list

    def get_host_row(self, host_name):
        """Locate host by name from host list and return the complete row"""
        return self.find_row_by_column_text(self.datatable, {self.host_name_td: host_name})

    def transition(self, host_name, transition_name):
        """Perform given transition on target host"""
        target_host_row = self.get_host_row(host_name)
        self.click_command_button(target_host_row, transition_name)

    def get_lnet_state(self, host_name):
        """Returns LNet state of given host"""

        target_host_row = self.get_host_row(host_name)
        tds = target_host_row.find_elements_by_tag_name("td")
        lnet_state = tds[self.lnet_state_td]
        return lnet_state.text

    def add_server_open(self):
        self.new_add_server_button.click()

    def add_server_enter_address(self, host_name):
        enter_text_for_element(self.driver, self.host_address_text, host_name)

    def add_server_submit_address(self):
        self.driver.find_element_by_css_selector(self.host_continue_button).click()
        self.quiesce()

    def add_server_confirm(self):
        self.driver.find_element_by_css_selector(self.add_host_confirm_button).click()
        self.quiesce()

    def add_server_close(self):
        self.driver.find_element_by_css_selector(self.add_host_close_button).click()

    def add_server_add_another(self):
        find_visible_element_by_css_selector(self.driver, self.add_host_add_another_button).click()

    @property
    def add_server_error(self):
        return self.get_input_error(self.driver.find_element_by_css_selector("input.add_host_address"))

    def add_servers(self, host_list):
        for host in host_list:
            host_name = host["address"]

            self.add_server_open()
            self.add_server_enter_address(host_name)
            self.add_server_submit_address()
            self.add_server_confirm()
            self.add_server_close()

        wait_for_transition(self.driver, self.long_wait)

    def remove_servers(self, host_list):
        for host in host_list:
            host_name = host["address"]
            self.transition(host_name, static_text['remove'])
