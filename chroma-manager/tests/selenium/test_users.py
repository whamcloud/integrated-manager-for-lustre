import re

from functools import partial

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from testconfig import config

from utils.sample_data import Testdata
from utils.messages_text import validation_messages

from tests.selenium.views.users import Users
from tests.selenium.base import SeleniumBaseTestCase
from tests.selenium.views.login import Login
from tests.selenium.utils.constants import wait_time
from tests.selenium.utils.element import enter_text_for_element, select_element_option


class SampleUser(object):
    def __init__(self, data):
        self.__dict__.update(data)

    def __getattr__(self, key):
        return self.__dict__[key]

    def __setattr__(self, key, val):
        self.__dict__[key] = val


class wrapped_login(object):
    def __init__(self, test_case, inner_user, outer_user=None, expecting_eula=False):
        self.test_case = test_case
        self.login_page = test_case.login_page
        self.inner_user = self.test_case.users[inner_user]
        self.expecting_eula = expecting_eula
        try:
            self.outer_user = self.test_case.users[outer_user]
        except KeyError:
            account = WebDriverWait(self.test_case.driver, wait_time['short']).until(
                EC.element_to_be_clickable((By.ID, 'account')), 'Account link not found.')
            self.outer_user = self.test_case.users[account.text]

    def __enter__(self):
        self.login_page.logout().login_and_accept_eula_if_presented(self.inner_user.username, self.inner_user.password)
        return self.inner_user

    def __exit__(self, type, value, tb):
        if tb is not None:
            # Don't swallow exceptions
            return False

        if self.outer_user:
            from selenium.common.exceptions import ElementNotVisibleException
            try:
                WebDriverWait(self.test_case.user_page, self.test_case.standard_wait).until(
                    lambda user: re.match('/ui/user/\d+/', user._get_url_parts()[2]) is None,
                    "Still on user account url."
                )
                self.test_case.user_page._reset_ui()
                self.test_case.navigation.logout()
            except ElementNotVisibleException:
                # I guess we're already logged out?
                pass

            self.login_page.login_and_accept_eula_if_presented(self.outer_user.username,
                                                               self.outer_user.password,
                                                               self.expecting_eula)


class TestUsers(SeleniumBaseTestCase):
    """Test cases for creating user and other user related operations"""
    def setUp(self):
        super(TestUsers, self).setUp()

        self.medium_wait = wait_time['medium']

        self.users = {}
        for user in Testdata().get_test_data_for_user():
            self.users[user['username']] = SampleUser(user)

        for user in config['chroma_managers'][0]['users']:
            if user['is_superuser']:
                self.users['admin'] = SampleUser(user)

        self.navigation.go('Configure', 'Users')
        self.login_page = Login(self.driver)
        self.user_page = Users(self.driver)

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
        user = self.users['superuser']
        self.add_user(user)
        self.user_page.create_new_user_button.click()
        select_element_option(self.driver, self.user_page.user_group, 0)
        enter_text_for_element(self.driver, self.user_page.username, user.username)
        self.driver.find_element_by_css_selector(self.user_page.create_user_button).click()
        self.user_page.quiesce()
        self.assertEqual(self.user_page.username_error, validation_messages['existing_username'])
        self.user_page.creation_dialog_close()
        self.delete_user(user)

    def test_entering_different_confirm_password(self):
        # Test validation for entering different confirm passwords
        user = self.users['superuser']
        self.user_page.create_new_user_button.click()
        select_element_option(self.driver, self.user_page.user_group, 0)
        enter_text_for_element(self.driver, self.user_page.username, 'fatfingers')
        enter_text_for_element(self.driver, self.user_page.password1, user.password)
        enter_text_for_element(self.driver, self.user_page.password2, user.password + "extra chars")
        self.driver.find_element_by_css_selector(self.user_page.create_user_button).click()
        self.user_page.quiesce()
        self.assertEqual(self.user_page.password2_error, validation_messages['different_password_values'])

    def test_superuser_powers(self):
        """Test that superuser powers work"""
        schmoe = self.users['schmoe']
        self.add_user(schmoe)
        self.verify_user(schmoe)

        self.navigation.go('Configure', 'Users')
        self.user_page.edit(schmoe.username, schmoe.new_email,
                            schmoe.first_name, schmoe.last_name)
        self.verify_edit(schmoe, email=schmoe.new_email)

        self.user_page.change_password(schmoe.username,
                                       schmoe.new_password,
                                       schmoe.new_confirm_password)
        schmoe.password = schmoe.new_password
        self.verify_user(schmoe)
        self.navigation.go('Configure', 'Users')
        self.user_page.edit_alerts(schmoe.username,
                                   schmoe.alert_type_subscriptions)
        with wrapped_login(self, schmoe.username):
            self.verify_alert_subscriptions(schmoe)
        self.navigation.go('Configure', 'Users')
        self.delete_user(schmoe)

    def test_adding_super_user(self):
        """Test that superusers can edit themselves and whatnot"""
        superuser = self.users['superuser']
        self.add_user(superuser)
        with wrapped_login(self, superuser.username):
            self.edit_user_password(superuser)
            self.edit_user_details(superuser)
        self.navigation.go('Configure', 'Users')
        self.delete_user(superuser)

    def del_user(self, user):
        """Delete a user"""
        self.navigation.go('Configure', 'Users')
        self.delete_user(user)

    def create_and_destroy_user(self, user):
        """HOF. Creates a user.

        :param user: object
        :returns function:
        """
        self.add_user(user)

        def create_and_destroy_user_inner(fn):
            """HOF INNER, after running fn, it deletes the user.

            :param fn: function
            """
            with wrapped_login(self, user.username):
                fn(user)
            self.del_user(user)

        return create_and_destroy_user_inner

    def test_adding_filesystem_user(self):
        """Test that fs users can be added"""
        create_destroy_user_and = self.create_and_destroy_user(self.users['fsuser'])
        create_destroy_user_and(self.verify_user)

    def test_edit_filesystem_user_password(self):
        """Test that fs users can edit password"""
        create_destroy_user_and = self.create_and_destroy_user(self.users['fsuser'])
        create_destroy_user_and(self.edit_user_password)

    def test_edit_filesystem_user_details(self):
        """Test that fs users can edit user details"""
        create_destroy_user_and = self.create_and_destroy_user(self.users['fsuser'])
        create_destroy_user_and(self.edit_user_details)

    def test_edit_filesystem_user_alert_subscriptions(self):
        """Test that fs users can edit alert subscriptions"""
        create_destroy_user_and = self.create_and_destroy_user(self.users['fsuser'])
        create_destroy_user_and(self.edit_alert_subscriptions)

    def test_resetting_eula(self):
        """Tests that resetting the eula will make the eula appear on next superuser login"""
        superuser = self.users["superuser"]
        self.add_user(superuser)
        with wrapped_login(self, superuser.username, True):
            self.user_page.reset_eula()

        self.navigation.go("Configure", "Users")
        self.delete_user(superuser)

    def test_non_superuser_does_not_see_reset_eula(self):
        """Tests that a non-superuser does not see the result eula checkbox in the account dialog"""
        fsuser = self.users["fsuser"]
        self.add_user(fsuser)

        the_call = partial(self.driver.find_element_by_css_selector, self.user_page.accept_eula_checkbox)

        with wrapped_login(self, fsuser.username):
            self.user_page.open_account_dialog()
            self.assertRaises(NoSuchElementException, the_call)
            self.user_page.close_account_dialog()

        self.navigation.go("Configure", "Users")
        self.delete_user(fsuser)

    def add_user(self, user, all_fields=False):
        # Add user
        self.user_page.create_new_user_button.click()
        if all_fields:
            self.user_page.add(user.user_group, user.username,
                               user.first_name, user.last_name, user.email,
                               user.password, user.confirm_password)
        else:
            # leave some fields blank to test that editing works
            self.user_page.add(user.user_group, user.username,
                               '', '', '', user.password, user.confirm_password)
        self.assertFalse(self.driver.find_element_by_css_selector(self.user_page.create_user_dialog).is_displayed())
        self.user_page = Users(self.driver)
        self.user_page.locate_user(user.username)

    def delete_user(self, user):
        # Delete user
        self.user_page.delete(user.username)

    def verify_edit(self, user, **kwargs):
        from copy import copy
        verify_user = copy(user)
        for arg in kwargs:
            setattr(verify_user, arg, kwargs[arg])
        target_host_row = self.user_page.locate_user(verify_user.username)
        fields = target_host_row.find_elements_by_tag_name("td")
        # username | full_name | email | roles
        self.assertEqual(fields[1].text, " ".join([verify_user.first_name, verify_user.last_name]).strip())
        self.assertEqual(fields[2].text, verify_user.email)

    def verify_user(self, user):
        """Try logging in as a particular user"""

        with wrapped_login(self, user.username):
            displayed_username = self.driver.find_element_by_css_selector('#account').text
            if not displayed_username == user.username:
                raise RuntimeError("Username markup is '%s', should be '%s'" % (displayed_username, user.username))

    def edit_user_password(self, user):
        """Test a user changing his own password"""

        self.user_page.edit_own_password(user.password, user.new_password)

        # Update the user instance so that future logins work OK
        user.password = user.new_password

        # Check that the new password has taken
        self.verify_user(user)

    def edit_user_details(self, user):
        """Test a user changing own details"""

        # As the user, edit and save own details
        self.user_page.edit_own_details(user.username, user.email,
                                        user.first_name, user.last_name)

        # Bit of a hack here, would be better to verify as the user themselves,
        # but then we'd need a separate code path.  This way we just log back
        # in as a superuser and reuse the same verify_edit() method.
        with wrapped_login(self, 'admin'):
            self.navigation.go('Configure', 'Users')
            # Verify that the edits made by the user stuck
            self.verify_edit(user)

    def edit_alert_subscriptions(self, user):
        """Test a user changing own alert subscriptions"""
        # First, subscribe to all, then test that we can uncheck
        # individual alert types.
        self.user_page.subscribe_to_all_alerts()
        self.user_page.edit_own_subscribed_alerts(user.alert_type_subscriptions)
        self.verify_alert_subscriptions(user)

        # Next, subscribe to none, then test that we can check
        # individual alert types.
        self.user_page.subscribe_to_no_alerts()
        self.user_page.edit_own_subscribed_alerts(user.alert_type_subscriptions)
        self.verify_alert_subscriptions(user)

    def verify_alert_subscriptions(self, user, **kwargs):
        from copy import copy
        verify_user = copy(user)
        for arg in kwargs:
            setattr(verify_user, arg, kwargs[arg])

        subscribed_alerts = self.user_page.list_own_subscribed_alerts()

        self.assertEqual(verify_user.alert_type_subscriptions, subscribed_alerts)
