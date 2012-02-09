""" Test Alerts"""

from utils.navigation import Navigation
from views.alerts import Alerts
from utils.constants import Constants
from base import SeleniumBaseTestCase


class Alertsdata(SeleniumBaseTestCase):

    def test_active_alerts_search(self):

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Alerts'])

        # Calling Alerts
        alerts_page = Alerts(self.driver)

        table_data = alerts_page.get_active_alerts_table_data()

        # Initialise the constants class
        constants = Constants()
        self.NO_DATATABLE_DATA = constants.get_static_text('no_data_for_datable')

        if table_data != self.NO_DATATABLE_DATA:
            entity_data = alerts_page.get_active_entity_data()
            alerts_page.enter_active_alert_search_data(entity_data)
            filtered_entity_data = alerts_page.get_active_entity_data()
            self.assertEqual(entity_data, filtered_entity_data)

    def test_alerts_history_search(self):

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Alerts'])

        # Calling Alerts
        alerts_page = Alerts(self.driver)

        table_data = alerts_page.get_history_table_data()

        # Initialise the constants class
        constants = Constants()
        self.NO_DATATABLE_DATA = constants.get_static_text('no_data_for_datable')

        if table_data != self.NO_DATATABLE_DATA:
            entity_data = alerts_page.get_history_entity_data()
            alerts_page.enter_alert_history_search_data(entity_data)
            filtered_entity_data = alerts_page.get_history_entity_data()
            self.assertEqual(entity_data, filtered_entity_data)

import unittest
if __name__ == '__main__':
    unittest.main()
