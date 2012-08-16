#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from tests.selenium.views.users import Users
from tests.selenium.base import SeleniumBaseTestCase
from utils.sample_data import Testdata
from tests.selenium.utils.navigation import Navigation
from utils.messages_text import validation_messages
from tests.selenium.base import enter_text_for_element
from tests.selenium.base import select_element_option
from tests.selenium.utils.constants import wait_time
from testconfig import config


class TestUsers(SeleniumBaseTestCase):
    """Test cases for creating user and other user related operations"""
    def setUp(self):
        super(TestUsers, self).setUp()

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

        # Test data for filesystem user
        self.fs_user_group = self.user_data[1]['user_group']
        self.fs_username = self.user_data[1]['username']
        self.fs_password = self.user_data[1]['password']
        self.fs_confirm_password = self.user_data[1]['confirm_password']
        self.fs_new_password = self.user_data[1]['new_password']
        self.fs_new_confirm_password = self.user_data[1]['new_confirm_password']

        # Test data for filesystem administrator
        self.admin_user_group = self.user_data[2]['user_group']
        self.admin_username = self.user_data[2]['username']
        self.admin_password = self.user_data[2]['password']
        self.admin_confirm_password = self.user_data[2]['confirm_password']
        self.admin_new_password = self.user_data[2]['new_password']
        self.admin_new_confirm_password = self.user_data[2]['new_confirm_password']

        for user in config['chroma_managers']['users']:
            if user['is_superuser']:
                self.superuser_username = user['username']
                self.superuser_password = user['password']

        self.navigation.go('Configure', 'Users')
        self.user_page = Users(self.driver)

    def test_add_super_user(self):
        # Test to add new user
        self.add_user(0, self.username, self.first_name, self.last_name, self.email, self.password, self.confirm_password)
        self.verify_user(self.username, self.password)
        navigation = Navigation(self.driver)
        navigation.go('Configure', 'Users')
        self.delete_user(self.username)

    def test_editing_super_user(self):
        # Test for editing user
        self.add_user(0, self.username, self.first_name, self.last_name, self.email, self.password, self.confirm_password)
        self.user_page.edit(self.username, self.new_password, self.new_confirm_password)
        self.assertFalse(self.user_page.edit_dialog_visible)
        self.user_page.locate_user(self.username)
        self.verify_user(self.username, self.new_password)
        navigation = Navigation(self.driver)
        navigation.go('Configure', 'Users')
        self.delete_user(self.username)

    def test_mandatory_fields(self):
        # Test validation for all mandatory fields
        self.user_page.create_new_user_button.click()
        self.driver.find_element_by_css_selector(self.user_page.create_user_button).click()
        self.user_page.quiesce()
        self.assertEqual(validation_messages['field_required'], self.user_page.username_error)
        self.assertEqual(validation_messages['field_required'], self.user_page.password_error)
        self.assertEqual(validation_messages['field_required'], self.user_page.password2_error)

    def test_adding_user_with_existing_username(self):
        # Test validation for duplicate username
        self.add_user(0, self.username, self.first_name, self.last_name, self.email, self.password, self.confirm_password)
        self.user_page.create_new_user_button.click()
        select_element_option(self.driver, self.user_page.user_group, 0)
        enter_text_for_element(self.driver, self.user_page.username, self.username)
        self.driver.find_element_by_css_selector(self.user_page.create_user_button).click()
        self.user_page.quiesce()
        self.assertEqual(self.user_page.username_error, validation_messages['existing_username'])
        self.user_page.creation_dialog_close()
        self.delete_user(self.username)

    def test_entering_different_confirm_password(self):
        # Test validation for entering different confirm passwords
        self.user_page.create_new_user_button.click()
        select_element_option(self.driver, self.user_page.user_group, 0)
        enter_text_for_element(self.driver, self.user_page.username, 'fatfingers')
        enter_text_for_element(self.driver, self.user_page.password1, self.password)
        enter_text_for_element(self.driver, self.user_page.password2, self.password + "extra chars")
        self.driver.find_element_by_css_selector(self.user_page.create_user_button).click()
        self.user_page.quiesce()
        self.assertEqual(self.user_page.password2_error, validation_messages['different_password_values'])

    def test_adding_filesystem_user(self):
        # Test to add new filesystem user
        self.add_user(1, self.fs_username, '', '', '', self.fs_password, self.fs_confirm_password)
        self.edit_user_password(self.fs_username, self.fs_password, self.fs_new_password)
        navigation = Navigation(self.driver)
        navigation.go('Configure', 'Users')
        self.delete_user(self.fs_username)

    def test_adding_filesystem_administrator_user(self):
        # Test to add new filesystem administrator user
        self.add_user(2, self.admin_username, '', '', '', self.admin_password, self.admin_confirm_password)
        self.edit_user_password(self.admin_username, self.admin_password, self.admin_new_password)
        navigation = Navigation(self.driver)
        navigation.go('Configure', 'Users')
        self.delete_user(self.admin_username)

    def add_user(self, user_group, username, first_name, last_name, email, password, confirm_password):
        # Add user
        self.user_page.create_new_user_button.click()
        self.user_page.add(user_group, username, first_name, last_name, email, password, confirm_password)
        self.assertFalse(self.driver.find_element_by_css_selector(self.user_page.create_user_dialog).is_displayed())
        self.user_page = Users(self.driver)
        self.user_page.locate_user(username)

    def delete_user(self, username):
        # Delete user
        self.user_page.delete(username)

    def verify_user(self, username, password):
        """Try logging in as a particular user"""

        self.navigation.logout()
        self.navigation.login(username, password)
        displayed_username = self.driver.find_element_by_css_selector('#username').text
        if not displayed_username == username:
            raise RuntimeError("Username markup is '%s', should be '%s'" % (displayed_username, username))
        self.navigation.logout()
        self.navigation.login(self.superuser_username, self.superuser_password)

    def edit_user_password(self, username, password, new_password):
        """Test a user changing his own password"""

        # Login as the user in question
        self.navigation.logout()
        self.navigation.login(username, password)

        self.user_page.edit_own_password(password, new_password)

        # Check that the new password has taken
        self.navigation.logout()
        self.navigation.login(username, new_password)

        # Return to the usual test running account
        self.navigation.logout()
        self.navigation.login(self.superuser_username, self.superuser_password)
