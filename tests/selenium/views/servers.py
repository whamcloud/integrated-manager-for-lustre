"""Page Object of mgt creation"""

from utils.constants import Constants
from time import sleep


class Servers:
    """ Page Object for mgt creation
    """
    def __init__(self, driver):
        self.driver = driver
        #Initialise the constants class
        constants = Constants()
        self.WAIT_TIME = constants.wait_time['standard']

        # Initialise all elements on that view.
        self.new_add_server_button = self.driver.find_element_by_id('btnAddNewHost')
        self.host_continue_button = self.driver.find_element_by_class_name('add_host_submit_button')
        self.add_host_confirm_button = self.driver.find_element_by_class_name('add_host_confirm_button')
        self.add_host_close_button = self.driver.find_element_by_class_name('add_host_close_button')

        self.add_dialog_div = self.driver.find_element_by_id('add_host_dialog')
        self.prompt_dialog_div = self.driver.find_element_by_id('add_host_prompt')
        self.loading_dialog_div = self.driver.find_element_by_id('add_host_loading')
        self.confirm_dialog_div = self.driver.find_element_by_id('add_host_confirm')
        self.complete_dialog_div = self.driver.find_element_by_id('add_host_complete')
        self.error_dialog_div = self.driver.find_element_by_id('add_host_error')

        self.host_address_text = self.driver.find_element_by_id('add_host_address')

    def click_new_server_add_button(self):
        #Click add server button
        self.new_add_server_button.click()
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    def enter_hostname(self):
        """Enter hostname"""
        self.host_address_text.clear()
        self.host_address_text.send_keys('clo-pune-linv17')

    def click_continue_button(self):
        #Click continue button
        self.host_continue_button.click()
        # FIXME: need to add a generic function to wait for an action

        loading_div = self.driver.find_element_by_class_name('loading_placeholder')
        for i in xrange(self.WAIT_TIME):
            if self.loading_dialog_div.is_displayed() and loading_div.text == 'Checking connectivity...':
                print "Checking connectivity..."
                sleep(2)
            else:
                break

    def loading_div_displayed(self):
        """Returns whether loading div is displayed or not"""
        self.loading_dialog_div.is_displayed()
        sleep(2)

    def confirm_div_displayed(self):
        """Returns whether confirm div is displayed or not"""
        return self.confirm_dialog_div.is_displayed()

    def click_confirm_button(self):
        #Click add server button
        self.add_host_confirm_button.click()
        # FIXME: need to add a generic function to wait for an action
        sleep(5)

    def complete_div_displayed(self):
        """Returns whether complete div is displayed or not"""
        return self.complete_dialog_div.is_displayed()

    def click_close_button(self):
        #Click close button
        self.add_host_close_button.click()
        sleep(2)
