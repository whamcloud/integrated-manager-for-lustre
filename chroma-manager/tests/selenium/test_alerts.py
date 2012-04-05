""" Test Alerts"""

from views.alerts import Alerts
from utils.constants import Constants
from base import SeleniumBaseTestCase


class TestAlerts(SeleniumBaseTestCase):
    def setUp(self):
        super(TestAlerts, self).setUp()

        self.navigation.go('Alerts')

        # Calling Alerts
        self.alerts_page = Alerts(self.driver)
        self.active_alert_data = self.alerts_page.get_active_alerts_table_data()
        self.history_table_data = self.alerts_page.get_history_table_data()

    def test_active_alerts_search(self):
        # Initialise the constants class
        constants = Constants()
        self.NO_DATATABLE_DATA = constants.get_static_text('no_data_for_datable')
        if self.active_alert_data != self.NO_DATATABLE_DATA:
            entity_data = self.alerts_page.get_active_entity_data()
            self.alerts_page.enter_active_alert_search_data(entity_data)
            filtered_entity_data = self.alerts_page.get_active_entity_data()
            self.assertEqual(entity_data, filtered_entity_data)

    def test_alerts_history_search(self):
        # Initialise the constants class
        constants = Constants()
        self.NO_DATATABLE_DATA = constants.get_static_text('no_data_for_datable')
        if self.history_table_data != self.NO_DATATABLE_DATA:
            entity_data = self.alerts_page.get_history_entity_data()
            self.alerts_page.enter_alert_history_search_data(entity_data)
            filtered_entity_data = self.alerts_page.get_history_entity_data()
            self.assertEqual(entity_data, filtered_entity_data)

import unittest
if __name__ == '__main__':
    unittest.main()
