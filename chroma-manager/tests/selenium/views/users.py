#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from tests.selenium.base import enter_text_for_element, element_visible
from tests.selenium.base import select_element_option
from tests.selenium.base import wait_for_element
from tests.selenium.base_view import DatatableView
from tests.selenium.utils.constants import static_text


class Users(DatatableView):
    datatable_id = "user_list"
    label_column = 0

    def __init__(self, driver):
        super(Users, self).__init__(driver)

        # Initialise elements on this page
        self.create_new_user_button = self.driver.find_element_by_css_selector("#create_user")
        self.create_user_dialog = "div.create_user_dialog"
        self.edit_user_dialog = "div.edit_user_dialog"
        self.delete_user_dialog = "div.delete_user_dialog"

        self.user_group = "div.create_user_dialog select"
        self.username = "div.create_user_dialog input[name=username]"
        self.first_name = "div.create_user_dialog input[name=first_name]"
        self.last_name = "div.create_user_dialog input[name=last_name]"
        self.email = "div.create_user_dialog input[name=email]"
        self.password1 = "div.create_user_dialog input[name=password1]"
        self.password2 = "div.create_user_dialog input[name=password2]"

        self.old_password = "div.edit_user_dialog input[name=old_password]"
        self.edit_password1 = "div.edit_user_dialog input[name=password1]"
        self.edit_password2 = "div.edit_user_dialog input[name=password2]"
        self.create_user_button = "button.create_button"
        self.edit_save_button = "button.save_button"
        self.delete_button = "button.delete_button"

        self.error_span = "span.error"
        self.user_list_datatable = 'user_list'
        self.username_td = 0
        self.user_group_td = 3

    def add(self, user_group, username, first_name, last_name, email, password, confirm_password):
        # Enter data for adding new user

        select_element_option(self.driver, self.user_group, user_group)
        enter_text_for_element(self.driver, self.username, username)
        enter_text_for_element(self.driver, self.first_name, first_name)
        enter_text_for_element(self.driver, self.last_name, last_name)
        enter_text_for_element(self.driver, self.email, email)
        enter_text_for_element(self.driver, self.password1, password)
        enter_text_for_element(self.driver, self.password2, confirm_password)

        # Click create button
        self.driver.find_element_by_css_selector(self.create_user_button).click()
        self.quiesce()

    def edit(self, username, new_password, new_confirm_password):
        # Edit user data
        target_host_row = self.locate_user(username)
        buttons = target_host_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == static_text['edit_user']:
                button.click()
                wait_for_element(self.driver, self.edit_user_dialog, self.medium_wait)
                enter_text_for_element(self.driver, self.edit_password1, new_password)
                enter_text_for_element(self.driver, self.edit_password2, new_confirm_password)
                # Click save button
                self.driver.find_element_by_css_selector(self.edit_save_button).click()
                self.quiesce()
                return

        raise RuntimeError("Cannot edit user with username " + username)

    def delete(self, username):
        # Delete user
        target_host_row = self.locate_user(username)
        buttons = target_host_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == static_text['delete_user']:
                button.click()
                wait_for_element(self.driver, self.delete_user_dialog, self.medium_wait)
                # Click delete button
                self.driver.find_element_by_css_selector(self.delete_button).click()
                return

        raise RuntimeError("Failed to find delete button for user %s" % username)

    def delete_all_except(self, protect_username):
        usernames = [row[0] for row in self.get_table_text(self.datatable, [self.username_td])]
        for username in [u for u in usernames if u != protect_username]:
            self.log.debug("Removing user %s" % username)
            self.delete(username)

    def locate_user(self, username):
        return self.find_row_by_column_text(self.datatable, {self.username_td: username})

    def edit_own_password(self, password, new_password):
        self.driver.find_element_by_css_selector("#account").click()
        self.quiesce()
        enter_text_for_element(self.driver, self.old_password, password)
        enter_text_for_element(self.driver, self.edit_password1, new_password)
        enter_text_for_element(self.driver, self.edit_password2, new_password)
        self.driver.find_element_by_css_selector(self.edit_save_button).click()
        self.quiesce()

    @property
    def edit_dialog_visible(self):
        return self.driver.find_element_by_css_selector(self.edit_user_dialog).is_displayed()

    @property
    def username_error(self):
        return self.get_input_error(self.driver.find_element_by_css_selector(self.username))

    @property
    def password_error(self):
        return self.get_input_error(self.driver.find_element_by_css_selector(self.password1))

    @property
    def password2_error(self):
        return self.get_input_error(self.driver.find_element_by_css_selector(self.password2))

    def creation_dialog_close(self):
        self.get_visible_element_by_css_selector(".cancel_button").click()
        assert not element_visible(self.driver, self.create_user_dialog)
