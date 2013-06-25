from tests.selenium.base import SeleniumBaseTestCase
from tests.selenium.utils.element import wait_for_element_by_css_selector
from tests.selenium.views.eula import Eula
from tests.selenium.views.users import Users
from utils.sample_data import Testdata
from tests.selenium.test_users import SampleUser
from testconfig import config


class TestEula(SeleniumBaseTestCase):
    def setUp(self):
        super_class = super(TestEula, self)

        #Override some setup code / settings since we are testing at an early stage.
        self.confirm_login = False
        self.accept_eula = lambda: None
        self.clear_all = lambda: None

        super_class.setUp()

        self.eula_page = Eula(self.driver)

    def test_eula_appears_for_superuser(self):
        """Tests that the eula will appear for the superuser if it has not been accepted yet."""
        self.assertTrue(self.eula_page.is_eula_visible())
        self.eula_page.accept_eula()

    def test_non_superuser_is_blocked(self):
        """Tests that a non-super user cannot access the application without a superuser accepting the eula."""
        fsuser = SampleUser(Testdata().get_test_data_for_user("fsuser"))
        wanted_keys = ["username", "first_name", "last_name", "email", "password", "confirm_password", "user_group"]
        kwargs = dict([(i, fsuser.__dict__[i]) for i in wanted_keys if i in fsuser.__dict__])

        self.eula_page.accept_eula()
        self.wait_for_login()
        self.navigation.go("Configure", "Users")

        users_page = Users(self.driver)
        users_page.create_new_user_button.click()
        users_page.add(**kwargs)
        users_page.reset_eula()

        self.navigation.logout()
        self.navigation.login(fsuser.username, fsuser.password, confirm_login=False)
        self.assertTrue(self.eula_page.is_access_denied_visible())
        self.driver.refresh()

        for user in config['chroma_managers'][0]['users']:
            if user['is_superuser']:
                debug = SampleUser(user)

        self.navigation.login(debug.username, debug.password, self.eula_page.accept_eula)
        self.navigation.go("Configure", "Users")
        users_page.delete(fsuser.username)

    def test_rejecting_eula(self):
        """Tests that rejecting the eula will not login the user"""
        self.eula_page.reject_eula()
        wait_for_element_by_css_selector(self.driver, "#user_info #anonymous #login", self.medium_wait)

        #No need to reset eula as we've never accepted it.
        self.reset_eula = lambda: None

    def test_accepting_eula(self):
        """Tests that accepting the eula will complete the login process"""
        self.eula_page.accept_eula()
        self.wait_for_login()
