
from selenium.common.exceptions import WebDriverException
from time import sleep
from base import wait_for_element
from testconfig import config


class Login:
    def __init__(self, driver):
        self.driver = driver
        self.open_dialog_button = self.driver.find_element_by_css_selector("#user_info #anonymous #login")
        self.username = self.driver.find_element_by_css_selector("#login_dialog input[name=username]")
        self.password = self.driver.find_element_by_css_selector("#login_dialog input[name=password]")
        self.login_button = self.driver.find_element_by_css_selector("#login_dialog + div #submit")

    def open_login_dialog(self):
        try:
            self.open_dialog_button.click()
            wait_for_element(self.driver, '#login_dialog input[name=username]', 1000)
        except WebDriverException:
            # open_dialog_button is not clickable so wait for jGrowl notifications to complete
            jGrowl_notifications = self.driver.find_element_by_id("jGrowl")
            for count in range(30):
                if jGrowl_notifications.text == "":
                    self.open_dialog_button.click()
                    return
                else:
                    sleep(1)
                    continue

    def login_superuser(self):
        for user in config['hydra_servers']['users']:
            if user['is_superuser']:
                self.username.send_keys(user['username'])
                self.password.send_keys(user['password'])
                self.login_button.click()
                return
        raise RuntimeError("No superuser in config file")
