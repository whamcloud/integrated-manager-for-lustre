#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from base import wait_for_transition
from utils.constants import wait_time
from utils.constants import static_text
from base import enter_text_for_element
from base import wait_for_element
from selenium.webdriver.support.ui import WebDriverWait


class Servers:
    """
    Page Object for server operations
    """
    def __init__(self, driver):
        self.driver = driver

        self.medium_wait = wait_time['medium']
        self.long_wait = wait_time['long']

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
        self.server_list_datatable = 'server_configuration_content'
        self.host_name_td = 0
        self.lnet_state_td = 1

    def verify_added_server(self, host_name):
        """Returns whether newly added server is listed or not"""
        self.locate_host(host_name)
        return True

    def get_server_list(self):
        """Returns server list"""
        server_list = self.driver.find_elements_by_xpath("id('" + self.server_list_datatable + "')/tr")

        # Get actual display text from list of webelement objects, append the names to a new list and sort the new list
        filtered_server_list = []
        for tr in server_list:
            tds = tr.find_elements_by_tag_name("td")
            filtered_server_list.append(tds[self.host_name_td].text)
        filtered_server_list.sort()
        return filtered_server_list

    def locate_host(self, host_name):
        """Locate host by name from host list and return the complete row"""

        server_list = self.driver.find_elements_by_xpath("id('" + self.server_list_datatable + "')/tr")
        for tr in server_list:
            tds = tr.find_elements_by_tag_name("td")
            if tds[self.host_name_td].text == host_name:
                return tr

        raise RuntimeError("Host: " + host_name + " not found in host list")

    def transition(self, host_name, transition_name):
        """Perform given transition on target host"""

        target_host_row = self.locate_host(host_name)
        buttons = target_host_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == transition_name:
                button.click()
                wait_for_transition(self.driver, self.long_wait)
                return

        raise RuntimeError("Cannot perform transition " + transition_name + " for host " + host_name)

    def get_lnet_state(self, host_name):
        """Returns LNet state of given host"""

        target_host_row = self.locate_host(host_name)
        tds = target_host_row.find_elements_by_tag_name("td")
        lnet_state = tds[self.lnet_state_td]
        return lnet_state.text

    def add_servers(self, host_list):
        for host in host_list:
            host_name = host["address"]

            self.new_add_server_button.click()
            enter_text_for_element(self.driver, self.host_address_text, host_name)
            self.driver.find_element_by_css_selector(self.host_continue_button).click()

            WebDriverWait(self.driver, self.medium_wait).until(lambda driver: self.driver.find_element_by_css_selector(self.loading_dialog_div).is_displayed())

            wait_for_element(self.driver, self.confirm_dialog_div, self.medium_wait)
            self.driver.find_element_by_css_selector(self.add_host_confirm_button).click()

            wait_for_element(self.driver, self.complete_dialog_div, self.medium_wait)
            self.driver.find_element_by_css_selector(self.add_host_close_button).click()

            wait_for_transition(self.driver, self.long_wait)

    def remove_servers(self, host_list):
        for host in host_list:
            host_name = host["address"]
            self.transition(host_name, static_text['remove'])
