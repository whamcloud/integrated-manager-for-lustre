from tests.selenium.utils.constants import static_text
from selenium.webdriver.support.ui import Select


class Logs:
    """
    Page Object for Logs Page
    """
    def __init__(self, driver):
        self.driver = driver

        self.NO_DATATABLE_DATA = static_text['no_data_for_datable']

        # Initialise elements on this page
        self.log_host_list = '#logs_hostList'
        self.logs_datatable = 'all_log_content'
        self.log_filter_btn = self.driver.find_element_by_css_selector('#log_filter_btn')

    def check_table_data(self):
        # Checks length of logs datatable. Throws exception if no data present.
        table_data = self.driver.find_element_by_xpath("id('" + self.logs_datatable + "')/tbody/tr/td")
        if table_data.text == self.NO_DATATABLE_DATA:
            raise RuntimeError("No data in table with ID: " + self.logs_datatable)

    def check_host_list_length(self):
        # Checks length of available hosts. Throws exception if no hosts available
        select_box_element = Select(self.driver.find_element_by_css_selector(self.log_host_list))
        if select_box_element.options.__len__() == 1:
            raise RuntimeError("No hosts available in host list")

    def get_host_value_from_table_data(self):
        """Returns host name on first row from log datatable"""
        host_name = self.driver.find_element_by_xpath("id('" + self.logs_datatable + "')/tbody/tr/td[2]")
        return host_name.text
