
import test_parameters


class Login:
    def __init__(self, driver):
        self.driver = driver
        self.open_dialog_button = self.driver.find_element_by_css_selector("#user_info #anonymous #login")
        self.username = self.driver.find_element_by_css_selector("input[name=username]")
        self.password = self.driver.find_element_by_css_selector("input[name=password]")
        self.login_button = self.driver.find_element_by_css_selector("#login_dialog + div #submit")

    def open_login_dialog(self):
        self.open_dialog_button.click()

    def login_superuser(self):
        for user in test_parameters.USERS:
            if user['is_superuser']:
                self.username.send_keys(user['username'])
                self.password.send_keys(user['password'])
                self.login_button.click()
                return
        raise RuntimeError("No superuser in test_parameters.USERS")
