from base import wait_for_element
from base import click_element_and_wait
from base import wait_for_transition


class Servers:
    """
    Page Object for server operations
    """
    def __init__(self, driver):
        self.driver = driver

        # Initialise elements on this page
        self.new_add_server_button = self.driver.find_element_by_css_selector('#btnAddNewHost')
        self.host_continue_button = self.driver.find_element_by_css_selector('a.add_host_submit_button')
        self.add_host_confirm_button = self.driver.find_element_by_css_selector('a.add_host_confirm_button')
        self.add_host_close_button = self.driver.find_element_by_css_selector('a.add_host_close_button')

        self.add_dialog_div = '#add_host_dialog'
        self.prompt_dialog_div = '#add_host_prompt'
        self.loading_dialog_div = '#add_host_loading'
        self.confirm_dialog_div = '#add_host_confirm'
        self.complete_dialog_div = '#add_host_complete'
        self.error_dialog_div = '#add_host_error'
        self.host_address_text = '#add_host_address'
        self.server_list_datatable = 'server_configuration_content'

    def verify_added_server(self, host_name):
        """Returns whether newly added server is listed or not"""
        self.locate_host(host_name)
        return True

    def get_server_list(self):
        """Returns server list"""
        server_list = self.driver.find_elements_by_xpath("id('" + self.server_list_datatable + "')/tr/td[1]")
        filtered_server_list = []
        for server_count in range(len(server_list)):
            filtered_server_list.append(server_list.__getitem__(server_count).text)
        filtered_server_list.sort()
        return filtered_server_list

    def locate_host(self, host_name):
        server_list = self.driver.find_elements_by_xpath("id('" + self.server_list_datatable + "')/tr/td[1]")
        for i in range(len(server_list)):
            if server_list.__getitem__(i).text == host_name:
                return str(i + 1)

        raise RuntimeError("Host: " + host_name + " not found in host list")

    def stop_lnet(self, host_name):
        """Stops LNet on the server"""

        row_number = self.locate_host(host_name)
        stop_lnet_selector = "id('" + self.server_list_datatable + "')/tr[" + row_number + "]/td[3]/span/button[3]"
        click_element_and_wait(self.driver, stop_lnet_selector, 10)

    def start_lnet(self, host_name):
        """Starts LNet on the server"""

        row_number = self.locate_host(host_name)
        start_lnet_selector = "id('" + self.server_list_datatable + "')/tr[" + row_number + "]/td[3]/span/button[1]"
        click_element_and_wait(self.driver, start_lnet_selector, 10)

    def unload_lnet(self, host_name):
        """Unloads LNet on the server"""

        row_number = self.locate_host(host_name)
        unload_lnet_selector = "id('" + self.server_list_datatable + "')/tr[" + row_number + "]/td[3]/span/button[2]"
        click_element_and_wait(self.driver, unload_lnet_selector, 10)

    def load_lnet(self, host_name):
        """Loads LNet on the server"""

        row_number = self.locate_host(host_name)
        load_lnet_selector = "id('" + self.server_list_datatable + "')/tr[" + row_number + "]/td[3]/span/button[3]"
        click_element_and_wait(self.driver, load_lnet_selector, 10)

    def remove_server(self, host_name):
        """Removes server"""

        row_number = self.locate_host(host_name)
        remove_server_selector = "id('" + self.server_list_datatable + "')/tr[" + row_number + "]/td[3]/span/button[2]"
        click_element_and_wait(self.driver, remove_server_selector, 10)
        wait_for_element(self.driver, '#transition_confirm_button', 10)
        self.driver.find_element_by_css_selector('#transition_confirm_button').click()
        wait_for_transition(self.driver, 10)

    def get_lnet_state(self, host_name):
        """Returns LNet state"""

        row_number = self.locate_host(host_name)
        lnet_state = self.driver.find_element_by_xpath("id('" + self.server_list_datatable + "')/tr[" + row_number + "]/td[2]/span")
        return lnet_state.text
