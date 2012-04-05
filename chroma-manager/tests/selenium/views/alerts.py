"""Page Object of Alerts page """
from utils.constants import Constants
from time import sleep


class Alerts:
    """ Page Object for Alerts Page
    """
    def __init__(self, driver):
        self.driver = driver
        #Initialise the constants class
        constants = Constants()
        self.WAIT_TIME = constants.wait_time['standard']

        # Initialise all elements on that view.
        self.active_alert_search_text = self.driver.find_element_by_xpath("id('active_AlertContent_filter')/label/input")
        self.alert_history_search_text = self.driver.find_element_by_xpath("id('all_AlertContent_filter')/label/input")

    def enter_active_alert_search_data(self, data):
        """ Enter data to be searched in active alerts
        @param: data : text to be set
        """
        # Enter data in alert history search box
        self.active_alert_search_text.clear()
        self.active_alert_search_text.send_keys(data)
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    def enter_alert_history_search_data(self, data):
        """ Enter data to be searched in alert history
        @param: data : text to be set
        """
        # Enter data in alert history search box
        self.alert_history_search_text.clear()
        self.alert_history_search_text.send_keys(data)
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    def get_active_alerts_table_data(self):
        """Returns text of first <td> tag of alerts table
        """
        active_AlertContent_processing = self.driver.find_element_by_id("active_AlertContent_processing")
        for i in xrange(self.WAIT_TIME):
            if active_AlertContent_processing.is_displayed():
                print "Loading data in active alerts table"
                sleep(2)
            else:
                table_data = self.driver.find_element_by_xpath("id('active_AlertContent')/tbody/tr/td")
                return table_data.text

    def get_active_entity_data(self):
        """Returns entity name of first row of active alerts table
        """
        entity_name = self.driver.find_element_by_xpath("id('active_AlertContent')/tbody/tr/td[2]")
        return entity_name.text

    def get_history_table_data(self):
        """Returns text of first <td> tag of alert history table to check whether data is displayed or not
        """
        all_AlertContent_processing = self.driver.find_element_by_id("all_AlertContent_processing")
        for i in xrange(self.WAIT_TIME):
            if all_AlertContent_processing.is_displayed():
                print "Loading data in alert history table"
                sleep(2)
            else:
                table_data = self.driver.find_element_by_xpath("id('all_AlertContent')/tbody/tr/td")
                return table_data.text

    def get_history_entity_data(self):
        """Returns entity name of first row of alert history table
        """
        entity_name = self.driver.find_element_by_xpath("id('all_AlertContent')/tbody/tr/td[3]")
        return entity_name.text
