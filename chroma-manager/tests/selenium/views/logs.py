"""Page Object of Logs Page"""
from utils.constants import Constants
from selenium.webdriver.support.ui import Select
from time import sleep


class Logs:
    """ Page Object for Logs
    """
    def __init__(self, driver):
        self.driver = driver
        #Initialise the constants class
        constants = Constants()
        self.WAIT_TIME = constants.wait_time

         # Initialise all elements on that view.
        self.log_host_list = self.driver.find_element_by_id('logs_hostList')
        self.log_date_from = self.driver.find_element_by_id('datetime_from')
        self.log_date_to = self.driver.find_element_by_id('datetime_to')
        self.only_lustre_checkbox = self.driver.find_element_by_id('id_only_lustre')
        self.log_filter_btn = self.driver.find_element_by_id('log_filter_btn')

    def click_filter(self):
        #Click filter button
        self.log_filter_btn.click()
        # FIXME: need to add a generic function to wait for an action
        sleep(5)

    def click_log_host_list(self, index):
        #Click severity select dropdown option
        self.log_host_options = self.log_host_list.find_elements_by_tag_name('option')
        self.log_host_options[index].click()
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    def get_table_data(self):
        """Returns text of first <td> tag of logs table
        """
        td = self.driver.find_element_by_xpath("id('all_log_content')/tbody/tr/td")
        return td.text

    def get_host_list_length(self):
        """Returns length of host dropdown list
        """
        self.log_host_options = self.log_host_list.find_elements_by_tag_name('option')
        option_values = [option.get_attribute('value') for option in self.log_host_options]
        return len(option_values)

    def get_host_value_from_dropdown(self):
        """Returns text of selected value from list from host dropdown
        """
        host_list = Select(self.log_host_list)
        for opt in host_list.options:
            if opt.is_selected():
                return opt.text

    def get_host_value_from_table_data(self):
        """Returns host name on first row from log table
        """
        host_name = self.driver.find_element_by_xpath("id('all_log_content')/tbody/tr/td[2]")
        return host_name.text
