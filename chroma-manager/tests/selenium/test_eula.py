from tests.selenium.base import SeleniumBaseTestCase
from tests.selenium.views.eula import Eula
from tests.selenium.views.login import Login
from tests.selenium.views.users import Users
from utils.sample_data import Testdata
from tests.selenium.test_users import SampleUser
from testconfig import config


class TestEula(SeleniumBaseTestCase):
    def setUp(self):
        super(TestEula, self).setUp()

        self.eula_page = Eula(self.driver)
        self.user_page = Users(self.driver)
        self.login_page = Login(self.driver)

        for user in config['chroma_managers'][0]['users']:
            if user['is_superuser']:
                self.debug = SampleUser(user)

    def test_non_superuser_is_blocked(self):
        """Tests that a non-super user cannot access the application without a superuser accepting the eula."""
        fsuser = SampleUser(Testdata().get_test_data_for_user("fsuser"))
        wanted_keys = ["username", "first_name", "last_name", "email", "password", "confirm_password", "user_group"]
        kwargs = dict([(i, fsuser.__dict__[i]) for i in wanted_keys if i in fsuser.__dict__])

        self.navigation.go("Configure", "Users")

        self.user_page.create_new_user_button.click()
        self.user_page.add(**kwargs)
        self.user_page.reset_eula()

        self.login_page.logout().login(fsuser.username, fsuser.password)

        self.login_page.wait_for_angular()

        self.eula_page.denied()

        self.login_page.login_and_accept_eula_if_presented(self.debug.username, self.debug.password)
        self.navigation.go("Configure", "Users")
        self.user_page.delete(fsuser.username)

    def test_rejecting_eula(self):
        """Tests that rejecting the eula will not login the user"""
        self.user_page.reset_eula()

        self.login_page.logout().login_and_reject_eula(self.debug.username, self.debug.password)
