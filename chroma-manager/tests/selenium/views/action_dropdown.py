from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from tests.selenium.base_view import BaseView
from tests.selenium.utils.command_monitor import wait_for_commands_to_finish
from tests.selenium.views.modal import ConfirmActionModal, CommandModal


class ActionDropdown(BaseView):
    def __init__(self, driver, dropdown_container):
        super(ActionDropdown, self).__init__(driver)
        self.dropdown_container = dropdown_container

    DROPDOWN = '.action-dropdown'
    DROPDOWN_BUTTON = '%s button' % DROPDOWN
    DROPDOWN_MENU = '%s .dropdown-menu' % DROPDOWN

    @property
    def dropdown_button(self):
        return self.dropdown_container.find_element_by_css_selector(self.DROPDOWN_BUTTON)

    @property
    def dropdown_menu(self):
        return self.dropdown_container.find_element_by_css_selector(self.DROPDOWN_MENU)

    def find_action_by_text(self, text):
        return self.dropdown_menu.find_element_by_link_text(text)

    def wait_for_dropdown_enabled(self):
        return WebDriverWait(self, self.long_wait).until(
            lambda action_dropdown: action_dropdown.dropdown_button.is_enabled())

    def click_action(self, action_text):
        confirm_action_modal = ConfirmActionModal(self.driver)
        command_modal = CommandModal(self.driver)

        wait_for_commands_to_finish(self.driver, self.long_wait)

        self.dropdown_button.location_once_scrolled_into_view

        self.wait_for_dropdown_enabled()
        self.dropdown_button.click()
        action = self.find_action_by_text(action_text)
        action.click()

        modal = None

        try:
            modal = confirm_action_modal.wait_for_modal(self.short_wait)
        except TimeoutException:
            pass

        if modal:
            confirm_action_modal.confirm_button.click()

            command_modal.wait_for_modal()
            command_modal.wait_for_close_button_to_be_clickable()
            command_modal.close_button.click()
            command_modal.wait_for_modal_remove()

            confirm_action_modal.wait_for_modal_remove()

        wait_for_commands_to_finish(self.driver, self.long_wait)

        def wait_for_remove(action_dropdown):
            try:
                return action_dropdown.dropdown_button
            except StaleElementReferenceException:
                return False

        WebDriverWait(self, self.short_wait).until_not(wait_for_remove, "Action drop down was not removed.")
