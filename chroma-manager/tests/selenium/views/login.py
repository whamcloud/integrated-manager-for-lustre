from tests.selenium.base_view import BaseView
from tests.selenium.utils.element import wait_for_element_by_css_selector


class Login(BaseView):
    def __init__(self, driver):
        super(Login, self).__init__(driver)

        self.open_dialog_button = self.driver.find_element_by_css_selector("#user_info #anonymous #login")
        self.username = self.driver.find_element_by_css_selector("#login_dialog input[name=username]")
        self.password = self.driver.find_element_by_css_selector("#login_dialog input[name=password]")
        self.login_button = self.driver.find_element_by_css_selector("#login_dialog + div #submit")

    def open_login_dialog(self):
        self.quiesce()
        self.open_dialog_button.click()
        wait_for_element_by_css_selector(self.driver, '#login_dialog input[name=username]', 10)

    def login_user(self, username, password):
        self.username.send_keys(username)
        self.password.send_keys(password)
        self.login_button.click()
