"""Page Object of file system creation"""
from utils.constants import Constants
from time import sleep
from selenium.webdriver.support.ui import Select


class CreateFilesystem:
    """ Page Object for file system creation
    """
    def __init__(self, driver):
        self.driver = driver
        #Initialise the constants class
        constants = Constants()
        self.WAIT_TIME = constants.wait_time
        # Initialise all elements on that view.
        self.file_system_name = self.driver.find_element_by_id('txtfsnameid')
        self.mgt_existing_dropdown = self.driver.find_element_by_id('mgt_existing_dropdown')
        self.mgt_chooser = self.driver.find_element_by_id('mgt_chooser')
        self.mdt_chooser = self.driver.find_element_by_id('mdt_chooser')
        self.ost_chooser = self.driver.find_element_by_id('ost_chooser')
        self.create_file_system_button = self.driver.find_element_by_id('btnCreateFS')
        self.fvc_selected = self.driver.find_elements_by_class_name("fvc_selected")

    def click_create_file_system_button(self):
        #Click create file system button
        self.create_file_system_button.click()
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    def enter_filesystem_name(self, filesystem_name):
        """Enter name for filesystem"""
        self.file_system_name.clear()
        self.file_system_name.send_keys(filesystem_name)

    def select_mgt(self, mgt_name):
        """Select an MGT"""
        mgt_list = Select(self.mgt_existing_dropdown)
        mgt_list.select_by_visible_text(mgt_name)

    def select_mdt(self, host_name, device_node):
        """Select an MDT"""
        mdtchooser = self.fvc_selected.__getitem__(1)
        mdtchooser.click()
        mdt_rows = self.driver.find_elements_by_xpath("id('mdt_chooser_table')/tbody/tr")
        for tr in mdt_rows:
            if tr.find_element_by_xpath("td[5]").text == host_name and tr.find_element_by_xpath("td[1]").text == device_node:
                tr.click()

    def select_ost(self, host_name, device_node):
        """Select an OST"""
        ost_rows = self.driver.find_elements_by_xpath("id('ost_chooser_table')/tbody/tr")
        for tr in ost_rows:
            if tr.find_element_by_xpath("td[5]").text == host_name and tr.find_element_by_xpath("td[1]").text == device_node:
                tr.click()

    def file_system_list_displayed(self):
        """Returns whether file system list is displayed or not"""
        self.fs_list = self.driver.find_element_by_id('fs_list')
        return self.fs_list.is_displayed()

    def new_file_system_name_displayed(self, filesystem_name):
        """Returns whether newly created file system is listed or not"""
        fs_list = self.driver.find_elements_by_xpath("id('fs_list')/tbody/tr/td/a")
        fs_name = ''
        if len(fs_list) > 0:
            for i in range(len(fs_list)):
                if fs_list.__getitem__(i).text == filesystem_name:
                    fs_name = fs_list.__getitem__(i).text
        return fs_name

    def error_dialog_displayed(self):
        """Returns whether error dialog is displayed or not"""
        self.popup_message = self.driver.find_element_by_id('popup_message')
        return self.popup_message.is_displayed()

    def error_dialog_message(self):
        """Returns error message displayed in error dialog box"""
        self.popup_message = self.driver.find_element_by_id('popup_message')
        return self.popup_message.text
