"""Page Object of mgt creation"""

from utils.constants import Constants
from time import sleep


class Mgt:
    """ Page Object for mgt creation
    """
    def __init__(self, driver):
        self.driver = driver
        #Initialise the constants class
        constants = Constants()
        self.WAIT_TIME = constants.wait_time

        # Initialise all elements on that view.
        self.fvc_selected = self.driver.find_elements_by_class_name("fvc_selected")
        self.create_mgt_button = self.driver.find_element_by_id('btnNewMGT')

    def select_mgt(self):
        """Select an MGT"""
        mgtchooser = self.fvc_selected.__getitem__(0)
        mgtchooser.click()
        sleep(2)
        mgt_rows = self.driver.find_elements_by_xpath("id('new_mgt_chooser_table')/tbody/tr/td")
        tr = mgt_rows.__getitem__(0)
        tr.click()

    def click_create_mgt(self):
        #Click create MGT button
        self.create_mgt_button.click()
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    def create_mgt_button_enabled(self):
        """Returns whether create MGT button is enabled or not"""
        return self.create_mgt_button.is_enabled()

    def mgt_list_displayed(self):
        """Returns whether MGT list is displayed or not"""
        self.mgt_list = self.driver.find_element_by_id('mgt_configuration')
        return self.mgt_list.is_displayed()

    def error_dialog_displayed(self):
        """Returns whether error dialog is displayed or not"""
        self.popup_message = self.driver.find_element_by_id('popup_message')
        return self.popup_message.is_displayed()
