"""Page Object of Events Page """
from utils.constants import Constants
from time import sleep
from selenium.webdriver.support.ui import Select


class Events:
    """ Page Object for Events Page
    """
    def __init__(self, driver):
        self.driver = driver
        #Initialise the constants class
        constants = Constants()
        self.WAIT_TIME = constants.wait_time

        # Initialise all elements on that view.
        self.host_list = self.driver.find_element_by_id('event_host')
        self.event_severity = self.driver.find_element_by_id('event_severity')
        self.event_type = self.driver.find_element_by_id('event_type')
        self.filter_btn = self.driver.find_element_by_id('filter_btn')

    def filter_records(self):
        #Click filter button
        self.filter_btn.click()
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    def select_host(self, index):
        #Click severity select dropdown option
        self.host_list_options = self.host_list.find_elements_by_tag_name('option')
        self.host_list_options[index].click()
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    def select_severity(self, index):
        #Click severity select dropdown option
        self.event_severity_options = self.event_severity.find_elements_by_tag_name('option')
        self.event_severity_options[index].click()
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    def get_table_data(self):
        """Returns text of first <td> tag of events table
        """
        td = self.driver.find_element_by_xpath("id('events_table')/tbody/tr/td")
        return td.text

    def get_host_value(self):
        """Returns text of first severity value from list in events table
        """
        td = self.driver.find_element_by_xpath("id('events_table')/tbody/tr/td[3]")
        return td.text

    def get_severity_value(self):
        """Returns text of first severity value from list in events table
        """
        td = self.driver.find_element_by_xpath("id('events_table')/tbody/tr/td[2]")
        return td.text

    def get_host_list_length(self):
        """Returns length of host dropdown list
        """
        self.log_host_options = self.host_list.find_elements_by_tag_name('option')
        option_values = [option.get_attribute('value') for option in self.log_host_options]
        return len(option_values)

    def get_host_value_from_dropdown(self):
        """Returns text of selected value from list from host dropdown
        """
        host_list = Select(self.host_list)
        for opt in host_list.options:
            if opt.is_selected():
                return opt.text
