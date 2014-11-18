from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from tests.selenium.utils.command_monitor import wait_for_commands_to_finish

from tests.selenium.base_view import BaseView
from tests.selenium.views.modal import CommandModal, AddServerModal
from tests.selenium.views.action_dropdown import ActionDropdown


class Servers(BaseView):
    """
    Page Object for server operations
    """
    def __init__(self, driver):
        super(Servers, self).__init__(driver)
        self._reset_ui(True)

    ADD_SERVER_BUTTON = '.add-server-button'
    SERVER_TABLE = '.server-table'

    @property
    def add_server_button(self):
        return self.driver.find_element_by_css_selector(self.ADD_SERVER_BUTTON)

    @property
    def server_table(self):
        return self.driver.find_element_by_css_selector(self.SERVER_TABLE)

    @property
    def first_row(self):
        """Return one tr element or None"""
        try:
            tr = self.server_table.find_element_by_css_selector('tbody tr:first-child')
        except NoSuchElementException:
            return None

        return tr

    def add_servers(self, host_list):
        command_modal = CommandModal(self.driver)
        add_server_modal = AddServerModal(self.driver)

        for host in host_list:
            host_name = host['address']

            # Step 1
            self.add_server_button.click()
            add_server_modal.wait_for_modal()
            add_server_modal.wait_for_title('Add Server - Add New Servers')
            add_server_modal.enter_address(host_name)
            add_server_modal.submit_address()

            # Step 2
            add_server_modal.wait_for_title('Add Server - Check Server Status')
            add_server_modal.wait_for_proceed_enabled()
            add_server_modal.proceed_button.click()
            command_modal.wait_for_modal()
            command_modal.wait_for_close_button_to_be_clickable()
            command_modal.close_button.click()
            command_modal.wait_for_modal_remove()

            # Step 3
            add_server_modal.wait_for_title('Add Server - Add Server Profiles')
            add_server_modal.wait_for_profile_select()
            add_server_modal.select_profile()
            add_server_modal.submit_profile()
            command_modal.wait_for_modal()
            command_modal.wait_for_close_button_to_be_clickable()
            command_modal.close_button.click()
            command_modal.wait_for_modal_remove()

            add_server_modal.wait_for_modal_remove()

            wait_for_commands_to_finish(self.driver, self.long_wait)

    def remove_all(self):
        row = self.first_row
        while row:
            prev_id = row.id
            ActionDropdown(self.driver, row).click_action('Remove')
            row = self.first_row
            if row and row.id == prev_id:
                raise StaleElementReferenceException("The element %s hasn't been removed" % row.text)
