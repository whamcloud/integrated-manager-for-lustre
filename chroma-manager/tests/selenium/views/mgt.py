"""Page Object of mgt creation"""
from utils.constants import Constants
from time import sleep
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
from base import wait_for_element


class Mgt:
    """ Page Object for mgt creation
    """
    def __init__(self, driver):
        self.driver = driver
        #Initialise the constants class
        constants = Constants()
        self.WAIT_TIME = constants.wait_time
        self.device_node_coloumn = 2
        self.host_name_coloumn = 5
        # Initialise all elements on that view.
        self.volume_chooser_selected = self.driver.find_elements_by_class_name("volume_chooser_selected")
        self.create_mgt_button = self.driver.find_element_by_id('btnNewMGT')
        self.selected_mgt_host = ""

    def select_mgt(self, host_name, device_node):
        """Select an MGT"""
        mgtchooser = self.volume_chooser_selected.__getitem__(0)
        mgtchooser.click()
        sleep(2)
        mgt_rows = self.driver.find_elements_by_xpath("id('new_mgt_chooser_table')/tbody/tr")
        for tr in mgt_rows:
            if tr.find_element_by_xpath("td[5]").text == host_name and tr.find_element_by_xpath("td[1]").text == device_node:
                tr.click()

    def check_mgt_actions(self, host_name, action_name):
        """Check whether the given action_name not present in available actions"""
        # When MGT is stopped no host_name is displayed so search by device_node
        if action_name == 'Start':
            mgt_list = self.driver.find_elements_by_xpath("id('mgt_configuration_content')/tr/td[" + str(self.device_node_coloumn) + "]")
        else:
            mgt_list = self.driver.find_elements_by_xpath("id('mgt_configuration_content')/tr/td[" + str(self.host_name_coloumn) + "]")
        is_compared = True
        for i in range(len(mgt_list)):
            if mgt_list.__getitem__(i).text == host_name:
                is_compared = False
                mgt_buttons = self.driver.find_elements_by_xpath("id('mgt_configuration_content')/tr[" + str(i + 1) + "]/td[6]/span/button")
                for button_count in range(len(mgt_buttons)):
                    if mgt_buttons[button_count].text == action_name:
                        return True

        return is_compared

    def create_mgt(self):
        self.create_mgt_button.click()
        # FIXME: need to add a generic function to wait for an action
        sleep(2)
        self.test_loading_image()

    def create_mgt_button_enabled(self):
        """Returns whether create MGT button is enabled or not"""
        return self.create_mgt_button.is_enabled()

    def verify_added_mgt(self, host_name):
        """Stops MGT on the server"""
        mgt_list = self.driver.find_elements_by_xpath("id('mgt_configuration_content')/tr/td[" + str(self.host_name_coloumn) + "]")
        if len(mgt_list) > 0:
            for i in range(len(mgt_list)):
                if mgt_list.__getitem__(i).text == host_name:
                    return True

    def mgt_list_displayed(self):
        """Returns whether MGT list is displayed or not"""
        self.mgt_list = self.driver.find_element_by_id('mgt_configuration')
        return self.mgt_list.is_displayed()

    def error_dialog_displayed(self):
        """Returns whether error dialog is displayed or not"""
        self.popup_message = self.driver.find_element_by_id('popup_message')
        return self.popup_message.is_displayed()

    def stop_mgt(self, host_name):
        """Stops MGT on the server"""
        mgt_list = self.driver.find_elements_by_xpath("id('mgt_configuration_content')/tr/td[" + str(self.host_name_coloumn) + "]")
        if len(mgt_list) > 0:
            for i in range(len(mgt_list)):
                if mgt_list.__getitem__(i).text == host_name:
                    stop_mgt_button = self.driver.find_element_by_xpath("id('mgt_configuration_content')/tr[" + str(i + 1) + "]/td[6]/span/button[2]")
                    stop_mgt_button.click()
                    wait_for_element(self.driver, '#transition_confirm_button', 10)
                    confirm_button = self.driver.find_element_by_id('transition_confirm_button')
                    confirm_button.click()
                    sleep(1)
                    self.test_loading_image()

    def start_mgt(self, device_node):
        """Starts MGT on the server"""
        mgt_list = self.driver.find_elements_by_xpath("id('mgt_configuration_content')/tr/td[" + str(self.device_node_coloumn) + "]")
        if len(mgt_list) > 0:
            for i in range(len(mgt_list)):
                if mgt_list.__getitem__(i).text == device_node:
                    start_mgt_button = self.driver.find_element_by_xpath("id('mgt_configuration_content')/tr[" + str(i + 1) + "]/td[6]/span/button[1]")
                    start_mgt_button.click()
                    sleep(2)
                    self.test_loading_image()

    def remove_mgt(self, host_name):
        """Removes MGT on the server"""
        mgt_list = self.driver.find_elements_by_xpath("id('mgt_configuration_content')/tr/td[" + str(self.host_name_coloumn) + "]")
        if len(mgt_list) > 0:
            for i in range(len(mgt_list)):
                if mgt_list.__getitem__(i).text == host_name:
                    stop_mgt_button = self.driver.find_element_by_xpath("id('mgt_configuration_content')/tr[" + str(i + 1) + "]/td[6]/span/button[1]")
                    stop_mgt_button.click()
                    wait_for_element(self.driver, '#transition_confirm_button', 10)
                    confirm_button = self.driver.find_element_by_id('transition_confirm_button')
                    confirm_button.click()
                    sleep(1)
                    self.test_loading_image()

    def test_loading_image(self):
        from time import sleep
        for i in xrange(10):
            print "Retrying attempt: " + str(i + 1)
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
