"""Page Object of Register User """

from utils.constants import Constants
from time import sleep


class Events:
    """ Page Object for User Registration
    """
    def __init__(self, driver):
        self.driver = driver
        #Initialise the constants class
        constants = Constants()
        self.WAIT_TIME = constants.wait_time

        # Initialise all elements on that view.
        self.host_list = self.driver.find_element_by_id('db_events_hostList')
        self.event_severity = self.driver.find_element_by_id('event_severity')
        self.event_type = self.driver.find_element_by_id('event_type')
        self.filter_btn = self.driver.find_element_by_id('filter_btn')

    def enter_event_filter_data(self):
        """ Enter data for events filter
        """

        # Start entering event filter data

        #Load the country list to find the right index
        self.event_severity_options = self.event_severity.find_elements_by_tag_name('option')
        option_values = [option.get_attribute('value') for option in self.event_severity_options]
        self.country_list[option_values(20)].click()

    def click_filter(self):
        #Click filter button
        self.filter_btn.click()
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    def click_severity_select(self, index):
        #Click severity select dropdown option
        self.event_severity_options = self.event_severity.find_elements_by_tag_name('option')
        self.event_severity_options[index].click()
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    #TODO: Handle negative tests, error messages

    def get_table_data(self):
        """Returns text of first <td> tag of events table
        """

        td = self.driver.find_element_by_xpath("/html/body/div[2]/div[3]/div/table/tbody/tr[2]/td/form/fieldset/div/table/tbody/tr/td")
        return td.text

    def get_severity_value(self):
        """Returns text of first severity value from list in events table
        """

        td = self.driver.find_element_by_xpath("/html/body/div[2]/div[3]/div/table/tbody/tr[2]/td/form/fieldset/div/table/tbody/tr/td[2]")
        return td.text
