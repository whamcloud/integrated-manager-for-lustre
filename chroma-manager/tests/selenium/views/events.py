from utils.constants import static_text
from selenium.webdriver.support.ui import Select


class Events:
    """
    Page Object for Events Page
    """
    def __init__(self, driver):
        self.driver = driver

        self.NO_DATATABLE_DATA = static_text['no_data_for_datable']

        # Initialise elements on this page
        self.host_list = '#event_host'
        self.event_severity = '#event_severity'
        self.event_type = 'event_type'
        self.events_datatable = 'events_table'

        self.filter_btn = self.driver.find_element_by_css_selector('#filter_btn')

    def check_table_data(self):
        # Checks length of events datatable. Throws exception if no data present
        table_data = self.driver.find_element_by_xpath("id('" + self.events_datatable + "')/tbody/tr/td")
        if table_data.text == self.NO_DATATABLE_DATA:
            raise RuntimeError("No data in table with ID: " + self.events_datatable)

    def get_host_value(self):
        # Returns text of first host value from events datatable
        td = self.driver.find_element_by_xpath("id('" + self.events_datatable + "')/tbody/tr/td[3]")
        return td.text

    def get_severity_value(self):
        # Returns text of first severity value from events datatable
        td = self.driver.find_element_by_xpath("id('" + self.events_datatable + "')/tbody/tr/td[2]")
        return td.text

    def check_host_list_length(self):
        # Checks length of available hosts. Throws exception if no hosts available
        select_box_element = Select(self.driver.find_element_by_css_selector(self.host_list))
        if select_box_element.options.__len__() == 1:
            raise RuntimeError("No hosts available in host list")
