
from time import sleep


class Login:
    def __init__(self, driver):
        self.driver = driver
        self.open_dialog_button = self.driver.find_element_by_css_selector("#user_info #anonymous #login")
        self.username = self.driver.find_element_by_css_selector("#login_dialog input[name=username]")
        self.password = self.driver.find_element_by_css_selector("#login_dialog input[name=password]")
        self.login_button = self.driver.find_element_by_css_selector("#login_dialog + div #submit")

    def open_login_dialog(self):
        from base import wait_for_element
        from base import element_visible
        for wait_before_count in xrange(10):
            is_overlay = element_visible(self.driver, "div.blockUI.blockOverlay")
            if is_overlay:
                sleep(2)
            else:
                self.open_dialog_button.click()
                wait_for_element(self.driver, '#login_dialog input[name=username]', 1000)
                break

    def login_user(self, username, password):
        self.username.send_keys(username)
        self.password.send_keys(password)
        self.login_button.click()
