"""Page Object of mgt creation"""

from utils.constants import Constants
from time import sleep
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException


class Filesystem:
    """ Page Object for mgt creation
    """
    def __init__(self, driver):
        self.driver = driver
        #Initialise the constants class
        constants = Constants()
        self.WAIT_TIME = constants.wait_time['standard']
        self.action_button_td = 7

    def stop_fs(self, filesystem_name):
        """Stops filesystem"""
        fs_list = self.driver.find_elements_by_xpath("id('fs_list')/tbody/tr/td[1]/a")
        if len(fs_list) > 0:
            for i in range(len(fs_list)):
                if fs_list.__getitem__(i).text == filesystem_name:
                    stop_lnet_button = self.driver.find_element_by_xpath("id('fs_list')/tr[" + str(i + 1) + "]/td[" + str(self.action_button_td) + "]/span/button[1]")
                    stop_lnet_button.click()
                    self.test_loading_image()

    def start_fs(self, filesystem_name):
        """Stops filesystem"""
        fs_list = self.driver.find_elements_by_xpath("id('fs_list')/tbody/tr/td[1]/a")
        if len(fs_list) > 0:
            for i in range(len(fs_list)):
                if fs_list.__getitem__(i).text == filesystem_name:
                    start_lnet_button = self.driver.find_element_by_xpath("id('fs_list')/tr[" + str(i + 1) + "]/td[" + str(self.action_button_td) + "]/span/button[1]")
                    start_lnet_button.click()
                    self.test_loading_image()

    def remove_fs(self, filesystem_name):
        """Removes filesystem"""
        fs_list = self.driver.find_elements_by_xpath("id('fs_list')/tbody/tr/td[1]/a")
        if len(fs_list) > 0:
            for i in range(len(fs_list)):
                if fs_list.__getitem__(i).text == filesystem_name:
                    remove_lnet_button = self.driver.find_element_by_xpath("id('fs_list')/tr[" + str(i + 1) + "]/td[" + str(self.action_button_td) + "]/span/button[2]")
                    remove_lnet_button.click()
                    sleep(5)
                    self.driver.find_element_by_id('transition_confirm_button').click()
                    self.test_loading_image()

    def check_fs_actions(self, fs_name, action_name):
        """Check whether the given action_name not present in available actions"""
        fs_list = self.driver.find_elements_by_xpath("id('fs_list')/tbody/tr/td[1]/a")
        if len(fs_list) > 0:
            for i in range(len(fs_list)):
                if fs_list.__getitem__(i).text == fs_name:
                    fs_buttons = self.driver.find_elements_by_xpath("id('fs_list')/tbody/tr[" + str(i + 1) + "]/td[" + str(self.action_button_td) + "]/span/button")
                    for i in range(len(fs_buttons)):
                        if fs_buttons[i].text == action_name:
                            return True
        return False

    def edit_fs_action(self, fs_name):
        fs_list = self.driver.find_elements_by_xpath("id('fs_list')/tbody/tr/td[1]/a")
        for fs in fs_list:
            if fs.text == fs_name:
                fs.click()

    def select_ost(self, host_name, device_node):
        """Select an OST"""
        create_ost_button = self.driver.find_element_by_id('btnNewOST')
        create_ost_button.click()
        sleep(2)
        ost_rows = self.driver.find_elements_by_xpath("id='new_ost_chooser_table']/tbody/tr")
        for tr in ost_rows:
            if tr.find_element_by_xpath("td[5]").text == host_name and tr.find_element_by_xpath("td[1]").text == device_node:
                tr.click()
        ok_button = self.driver.find_element_by_id('ost_ok_button')
        ok_button.click()

    def get_file_system_list_length(self):
        """Returns length of file system list"""
        fs_list = self.driver.find_elements_by_xpath("id('fs_list')/tbody/tr/td[1]/a")
        return len(fs_list)

    def test_loading_image(self):
        from time import sleep
        for i in xrange(10):
            print "Retrying attempt: " + str(i)
            try:
                loading_div = self.driver.find_element_by_css_selector("span.notification_object_icon.busy_icon")
                try:
                    if loading_div.is_displayed():
                        print "Waiting for process to get complete"
                        sleep(2)
                        continue
                except StaleElementReferenceException:
                    sleep(2)
                    return
            except NoSuchElementException:
                sleep(2)
                return
