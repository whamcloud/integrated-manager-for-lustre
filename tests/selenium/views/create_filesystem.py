"""Page Object of file system creation"""

from utils.constants import Constants
from time import sleep


class FileSystem:
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

    def enter_filesystem_data(self):

        # Enter file system name
        self.enter_filename()

        # Select MGT
        self.select_mgt()

        # Select MDT
        self.select_mdt()

        # Select OST
        self.select_ost()

    def click_create_file_system_button(self):
        #Click create file system button
        self.create_file_system_button.click()
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    def enter_filename(self):
        """Enter name for filesystem"""
        self.file_system_name.clear()
        self.file_system_name.send_keys('indifs01')

    def select_mgt(self):
        """Select an MGT"""
        mgtchooser = self.fvc_selected.__getitem__(0)
        mgtchooser.click()
        mgt_rows = self.driver.find_elements_by_xpath("/html/body/div[2]/div[3]/div/div/table/tbody/tr[2]/td/div[2]/div/div[2]/div/table/tbody/tr")
        tr = mgt_rows.__getitem__(0)
        tr.click()

    def select_mdt(self):
        """Select an MDT"""
        mdtchooser = self.fvc_selected.__getitem__(1)
        mdtchooser.click()
        mdt_rows = self.driver.find_elements_by_xpath("/html/body/div[2]/div[3]/div/div/table/tbody/tr[3]/td/div[2]/div/div[2]/div/table/tbody/tr")
        tr = mdt_rows.__getitem__(0)
        tr.click()

    def select_ost(self):
        """Select an OST"""
        ost_rows = self.driver.find_elements_by_xpath("/html/body/div[2]/div[3]/div/div/table/tbody/tr[4]/td/div[2]/div/div[2]/div/table/tbody/tr")
        tr = ost_rows.__getitem__(0)
        tr.click()

    def file_system_list_displayed(self):
        """Returns whether file system list is displayed or not"""
        self.fs_list = self.driver.find_element_by_id('fs_list')
        return self.fs_list.is_displayed()

    def new_file_system_name_displayed(self):
        """Returns whether newly created file system is listed or not"""
        fs_list = self.driver.find_elements_by_xpath("/html/body/div[2]/div[3]/div/div/div/table/tbody/tr/td/a")
        fs_name = ''
        if len(fs_list) > 0:
            for i in range(len(fs_list)):
                if fs_list.__getitem__(i).text == 'testfs01':
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
