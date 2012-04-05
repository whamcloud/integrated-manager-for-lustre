"""Page Object of breadcrumb """

from selenium.webdriver.support.ui import WebDriverWait
from utils.constants import Constants


class Breadcrumb:
    """ Page Object for Breadcrumb
    """
    def __init__(self, driver):
        self.driver = driver

        # Initialise all elements in breadcrumb on dashboard
        self.selectView = self.driver.find_element_by_id('selectView')
        self.fsSelect = self.driver.find_element_by_id('fsSelect')
        self.db_polling_element = self.driver.find_element_by_id('db_polling_element')
        self.intervalSelect = self.driver.find_element_by_id('intervalSelect')
        self.unitSelect = self.driver.find_element_by_id('unitSelect')
        constants = Constants()
        self.medium_wait_time = constants.get_wait_time('medium')

    def select_view(self, index):
        # Select view from dropdown
        view_options = self.selectView.find_elements_by_tag_name('option')
        view_options[index].click()
        serverSelect = self.driver.find_element_by_id('serverSelect')
        WebDriverWait(self.driver, self.medium_wait_time).until(lambda driver: serverSelect.is_displayed())

    def select_time_interval(self, index):
        # Select option from time_interval dropdown
        time_interval_options = self.intervalSelect.find_elements_by_tag_name('option')
        time_interval_options[index].click()

    def get_unit_list_length(self):
        """Returns length of units list"""
        units_list_options = self.unitSelect.find_elements_by_tag_name('option')
        # -1 as first option is "Select"
        return len(units_list_options) - 1

    def get_filesystem_list_length(self):
        """Returns length of file system list"""
        file_system_list_options = self.fsSelect.find_elements_by_tag_name('option')
        return len(file_system_list_options)

    def server_list_length(self):
        """Returns length of server list"""
        serverSelect = self.driver.find_element_by_id('serverSelect')
        server_list_options = serverSelect.find_elements_by_tag_name('option')
        # -1 as first option is "Select Server"
        return len(server_list_options) - 1
