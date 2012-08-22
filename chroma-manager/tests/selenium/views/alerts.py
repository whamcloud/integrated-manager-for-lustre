from tests.selenium.utils.constants import static_text


class Alerts:
    """
    Page Object for Alerts Page
    """
    def __init__(self, driver):
        self.driver = driver

        self.NO_DATATABLE_DATA = static_text['no_data_for_datable']

        # Initialise elements on this page
        self.active_alert_search_text = "#active_AlertContent_filter label input"
        self.alert_history_search_text = "#all_AlertContent_filter label input"
        self.active_alert_datatable = 'active_AlertContent'
        self.alert_history_datatable = 'all_AlertContent'

    def get_active_alert_entity_data(self):
        """
        Returns entity name from last row of active alerts table
        """
        entity_names = self.driver.find_elements_by_xpath("id('" + self.active_alert_datatable + "')/tbody/tr/td[2]")
        return entity_names.__getitem__(len(entity_names) - 1).text

    def get_alert_history_entity_data(self):
        """
        Returns entity name from last row of alert history table
        """
        entity_names = self.driver.find_elements_by_xpath("id('" + self.alert_history_datatable + "')/tbody/tr/td[3]")
        return entity_names.__getitem__(len(entity_names) - 1).text

    def get_table_data(self, table_id):
        """
        Returns entity name of first <td> tag of given table if present, otherwise throws exception
        """
        table_data = self.driver.find_element_by_xpath("id('" + table_id + "')/tbody/tr/td")
        if table_data.text == self.NO_DATATABLE_DATA:
            raise RuntimeError("No data in table with ID: " + table_id)
        else:
            if table_id == self.active_alert_datatable:
                entity_name = self.driver.find_element_by_xpath("id('" + table_id + "')/tbody/tr/td[2]")
            else:
                entity_name = self.driver.find_element_by_xpath("id('" + table_id + "')/tbody/tr/td[3]")

            return entity_name.text
