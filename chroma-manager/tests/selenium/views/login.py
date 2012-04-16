
from time import sleep
from base import wait_for_element
from testconfig import config
from base import element_visible


class Login:
    def __init__(self, driver):
        self.driver = driver
        self.open_dialog_button = self.driver.find_element_by_css_selector("#user_info #anonymous #login")
        self.username = self.driver.find_element_by_css_selector("#login_dialog input[name=username]")
        self.password = self.driver.find_element_by_css_selector("#login_dialog input[name=password]")
        self.login_button = self.driver.find_element_by_css_selector("#login_dialog + div #submit")

    def open_login_dialog(self):
        for wait_before_count in xrange(10):
            is_overlay = element_visible(self.driver, "div.blockUI.blockOverlay")
            if is_overlay:
                sleep(2)
            else:
                self.open_dialog_button.click()
                wait_for_element(self.driver, '#login_dialog input[name=username]', 1000)
                break

    def login_superuser(self):
        for user in config['chroma_managers']['users']:
            if user['is_superuser']:
                self.username.send_keys(user['username'])
                self.password.send_keys(user['password'])
                self.login_button.click()
                return
        raise RuntimeError("No superuser in config file")

    def login_newuser(self, username, password):
        self.username.send_keys(username)
        self.password.send_keys(password)
        self.login_button.click()
