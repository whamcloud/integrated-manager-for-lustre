#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from tests.selenium.base import wait_for_transition
from tests.selenium.base_view import DatatableView
from tests.selenium.utils.constants import static_text
from tests.selenium.base import enter_text_for_element


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
        self.add_host_close_button = 'a.add_host_close_button'

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

    def verify_added_server(self, host_name):
        """Returns whether newly added server is listed or not"""
        self.get_host_row(host_name)
        return True

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

    def add_servers(self, host_list):
        for host in host_list:
            host_name = host["address"]

            self.new_add_server_button.click()
            enter_text_for_element(self.driver, self.host_address_text, host_name)
            self.driver.find_element_by_css_selector(self.host_continue_button).click()
            self.quiesce()

            self.driver.find_element_by_css_selector(self.add_host_confirm_button).click()
            self.quiesce()

            self.driver.find_element_by_css_selector(self.add_host_close_button).click()

            wait_for_transition(self.driver, self.long_wait)

    def remove_servers(self, host_list):
        for host in host_list:
            host_name = host["address"]
            self.transition(host_name, static_text['remove'])
