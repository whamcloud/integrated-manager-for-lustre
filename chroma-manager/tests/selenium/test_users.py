#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import django.utils.unittest
from views.users import Users
from base import SeleniumBaseTestCase
from utils.sample_data import Testdata
from base import wait_for_datatable
from utils.navigation import Navigation
from utils.messages_text import validation_messages
from base import enter_text_for_element
from base import select_element_option
from base import wait_for_element
from utils.constants import wait_time


class TestUsers(SeleniumBaseTestCase):
    """Test cases for creating user and other user related operations"""
    def setUp(self):
        super(TestUsers, self).setUp()

        self.navigation.go('Configure', 'Users')
        self.medium_wait = wait_time['medium']

        # Getting test data for servers
        self.test_data = Testdata()
        self.user_data = self.test_data.get_test_data_for_user()
        self.user_group = self.user_data[0]['user_group']
        self.username = self.user_data[0]['username']
        self.first_name = self.user_data[0]['first_name']
        self.last_name = self.user_data[0]['last_name']
        self.email = self.user_data[0]['email']
        self.password = self.user_data[0]['password']
        self.confirm_password = self.user_data[0]['confirm_password']
        self.new_password = self.user_data[0]['new_password']
        self.new_confirm_password = self.user_data[0]['new_confirm_password']

        # Test data for file system user
        self.fs_user_group = self.user_data[1]['user_group']
        self.fs_username = self.user_data[1]['username']
        self.fs_password = self.user_data[1]['password']
        self.fs_confirm_password = self.user_data[1]['confirm_password']
        self.fs_new_password = self.user_data[1]['new_password']
        self.fs_new_confirm_password = self.user_data[1]['new_confirm_password']

        # Test data for file system user
        self.admin_user_group = self.user_data[2]['user_group']
        self.admin_username = self.user_data[2]['username']
        self.admin_password = self.user_data[2]['password']
        self.admin_confirm_password = self.user_data[2]['confirm_password']
        self.admin_new_password = self.user_data[2]['new_password']
        self.admin_new_confirm_password = self.user_data[2]['new_confirm_password']

        self.user_page = Users(self.driver)
        wait_for_datatable(self.driver, '#user_list')

    def test_add_super_user(self):
        # Test to add new user
        self.add_user(0, self.username, self.first_name, self.last_name, self.email, self.password, self.confirm_password)
        self.user_page.verify_user(self.username, self.password)
        navigation = Navigation(self.driver)
        navigation.go('Configure', 'Users')
        self.delete_user(self.username)

    def test_editing_super_user(self):
        # Test for editing user
        self.add_user(0, self.username, self.first_name, self.last_name, self.email, self.password, self.confirm_password)
        self.user_page.edit(self.username, self.new_password, self.new_confirm_password)
        self.assertFalse(self.driver.find_element_by_css_selector(self.user_page.edit_user_dialog).is_displayed())
        self.driver.refresh()
        self.user_page = Users(self.driver)
        self.user_page.locate_user(self.username)
        self.user_page.verify_user(self.username, self.new_password)
        navigation = Navigation(self.driver)
        navigation.go('Configure', 'Users')
        self.delete_user(self.username)

    def test_mandatory_fields(self):
        self.user_page.create_new_user_button.click()
        self.driver.find_element_by_css_selector(self.user_page.create_user_button).click()
        wait_for_element(self.driver, self.user_page.error_span, self.medium_wait)
        error_message = self.driver.find_elements_by_css_selector(self.user_page.error_span)
        self.assertEqual(validation_messages['field_required'], error_message[0].text, 'Error message for blank username not displayed')
        self.assertEqual(validation_messages['field_required'], error_message[1].text, 'Error message for blank password not displayed')
        self.assertEqual(validation_messages['field_required'], error_message[2].text, 'Error message for blank confirm password not displayed')

    def test_adding_user_with_existing_username(self):
        self.add_user(0, self.username, self.first_name, self.last_name, self.email, self.password, self.confirm_password)
        self.user_page.create_new_user_button.click()
        select_element_option(self.driver, self.user_page.user_group, 0)
        enter_text_for_element(self.driver, self.user_page.username, self.username)
        self.driver.find_element_by_css_selector(self.user_page.create_user_button).click()
        wait_for_element(self.driver, self.user_page.error_span, self.medium_wait)
        error_message = self.driver.find_elements_by_css_selector(self.user_page.error_span)
        self.assertEqual(validation_messages['existing_username'], error_message[0].text, 'Error message for adding duplicate username not displayed')
        self.driver.refresh()
        self.delete_user(self.username)

    def test_entering_different_confirm_password(self):
        self.user_page.create_new_user_button.click()
        import random
        select_element_option(self.driver, self.user_page.user_group, 0)
        enter_text_for_element(self.driver, self.user_page.username, 'user' + str(random.random()))
        enter_text_for_element(self.driver, self.user_page.password1, self.password)
        enter_text_for_element(self.driver, self.user_page.password2, str(random.random()))
        self.driver.find_element_by_css_selector(self.user_page.create_user_button).click()
        wait_for_element(self.driver, self.user_page.error_span, self.medium_wait)
        error_message = self.driver.find_elements_by_css_selector(self.user_page.error_span)
        self.assertEqual(validation_messages['different_password_values'], error_message[0].text, 'No error message displayed when different values are entered for password and confirm password fields')

    def test_adding_filesystem_user(self):
        # Test to add new user
        self.add_user(1, self.fs_username, '', '', '', self.fs_password, self.fs_confirm_password)
        self.user_page.edit_user_password(self.fs_username, self.fs_password, self.fs_new_password)
        navigation = Navigation(self.driver)
        navigation.go('Configure', 'Users')
        self.delete_user(self.fs_username)

    def test_adding_filesystem_administrator_user(self):
        # Test to add new user
        self.add_user(2, self.admin_username, '', '', '', self.admin_password, self.admin_confirm_password)
        self.user_page.edit_user_password(self.admin_username, self.admin_password, self.admin_new_password)
        navigation = Navigation(self.driver)
        navigation.go('Configure', 'Users')
        self.delete_user(self.admin_username)

    def add_user(self, user_group, username, first_name, last_name, email, password, confirm_password):
        # Add user
        self.user_page.create_new_user_button.click()
        self.user_page.add(user_group, username, first_name, last_name, email, password, confirm_password)
        self.assertFalse(self.driver.find_element_by_css_selector(self.user_page.create_user_dialog).is_displayed())
        self.driver.refresh()
        self.user_page = Users(self.driver)
        self.user_page.locate_user(username)

    def delete_user(self, username):
        # Delete user
        self.user_page.delete(username)

if __name__ == '__main__':
    django.utils.unittest.main()
