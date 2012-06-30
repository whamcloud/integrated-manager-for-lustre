#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from tests.selenium.base import enter_text_for_element
from tests.selenium.base import select_element_option
from tests.selenium.base import wait_for_element
from tests.selenium.utils.constants import wait_time
from tests.selenium.utils.constants import static_text
from tests.selenium.base import login
from testconfig import config


class Users:
    """
    Page Object for user operations
    """
    def __init__(self, driver):
        self.driver = driver

        self.medium_wait = wait_time['medium']

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

        for user in config['chroma_managers']['users']:
            if user['is_superuser']:
                self.superuser_username = user['username']
                self.superuser_password = user['password']

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
                return

        raise RuntimeError("Cannot edit user with username " + username)

    def delete(self, username):
        # Delete userv
        target_host_row = self.locate_user(username)
        buttons = target_host_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == static_text['delete_user']:
                button.click()
                wait_for_element(self.driver, self.delete_user_dialog, self.medium_wait)
                # Click delete button
                self.driver.find_element_by_css_selector(self.delete_button).click()
                return

        raise RuntimeError("Cannot delete user with username " + username)

    def locate_user(self, username):
        """Locate user by username and group from users list and return the complete row"""
        users_list = self.driver.find_elements_by_xpath("id('" + self.user_list_datatable + "')/tbody/tr")
        for tr in users_list:
            tds = tr.find_elements_by_tag_name("td")
            if tds[self.username_td].text == username:
                return tr

        raise RuntimeError("User with username: " + username + " not found in list")

    def verify_user(self, username, password):
        self.driver.find_element_by_css_selector("#logout").click()
        login(self.driver, username, password)
        wait_for_element(self.driver, '#configure_menu', 10)
        self.driver.find_element_by_css_selector("#logout").click()
        login(self.driver, self.superuser_username, self.superuser_password)

    def edit_user_password(self, username, password, new_password):
        self.driver.find_element_by_css_selector("#logout").click()
        login(self.driver, username, password)
        wait_for_element(self.driver, '#username', 10)
        self.driver.find_element_by_css_selector("#username").click()
        wait_for_element(self.driver, self.edit_user_dialog, 10)
        enter_text_for_element(self.driver, self.old_password, password)
        enter_text_for_element(self.driver, self.edit_password1, new_password)
        enter_text_for_element(self.driver, self.edit_password2, new_password)
        # Click save button
        self.driver.find_element_by_css_selector(self.edit_save_button).click()
        wait_for_element(self.driver, '#username', 10)
        self.driver.find_element_by_css_selector("#logout").click()
        login(self.driver, username, new_password)
        wait_for_element(self.driver, '#username', 10)
        self.driver.refresh()
        self.driver.find_element_by_css_selector("#logout").click()
        login(self.driver, self.superuser_username, self.superuser_password)
