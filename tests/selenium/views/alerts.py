"""Page Object of Logs """

from utils.constants import Constants
from time import sleep


class Alerts:
    """ Page Object for Logs
    """
    def __init__(self, driver):
        self.driver = driver
        #Initialise the constants class
        constants = Constants()
        self.WAIT_TIME = constants.wait_time

        # Initialise all elements on that view.
        self.alert_history_search_text = self.driver.find_element_by_xpath('/html/body/div[2]/div[3]/div/table/tbody/tr[3]/td/fieldset/div/div/div[2]/label/input')

    def enter_search_data(self, data):
        """ Register a new user
        @param: user : an object of UserDetails, a custom dict
        """

        # Enter data in alert history search box
        self.alert_history_search_text.clear()
        self.alert_history_search_text.send_keys(data)
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    def get_active_alerts_table_data(self):
        """Returns text of first <td> tag of events table
        """

        table_data = self.driver.find_element_by_xpath("/html/body/div[2]/div[3]/div/table/tbody/tr[2]/td/fieldset/div/table/tbody/tr/td")
        return table_data.text

    def get_active_entity_data(self):
        """Returns text of first <td> tag of events table
        """

        entity_name = self.driver.find_element_by_xpath("/html/body/div[2]/div[3]/div/table/tbody/tr[2]/td/fieldset/div/table/tbody/tr/td[2]")
        return entity_name.text

    def get_history_table_data(self):
        """Returns text of first <td> tag of events table to check whether data is displayed or not
        """

        table_data = self.driver.find_element_by_xpath("/html/body/div[2]/div[3]/div/table/tbody/tr[3]/td/fieldset/div/table/tbody/tr/td")
        return table_data.text

    def get_history_entity_data(self):
        """Returns text of first <td> tag of events table
        """

        entity_name = self.driver.find_element_by_xpath("/html/body/div[2]/div[3]/div/table/tbody/tr[3]/td/fieldset/div/table/tbody/tr/td[3]")
        return entity_name.text
