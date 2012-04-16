from views.alerts import Alerts
from base import SeleniumBaseTestCase
from base import enter_text_for_element
from base import wait_for_datatable


class TestAlerts(SeleniumBaseTestCase):
    """Test cases for alerts page"""

    def setUp(self):
        super(TestAlerts, self).setUp()

        self.navigation.go('Alerts')
        self.alerts_page = Alerts(self.driver)

        wait_for_datatable(self.driver, '#active_AlertContent')
        wait_for_datatable(self.driver, '#all_AlertContent')

    def test_active_alerts_search(self):
        """Test active alert search"""

        active_alert_data = self.alerts_page.get_table_data(self.alerts_page.active_alert_datatable)
        enter_text_for_element(self.driver, self.alerts_page.active_alert_search_text, active_alert_data)

        filtered_entity_data = self.alerts_page.get_active_alert_entity_data()
        self.assertEqual(active_alert_data, filtered_entity_data, "Searched data in active alerts not matching")

    def test_alerts_history_search(self):
        """Test alert history search"""

        history_table_data = self.alerts_page.get_table_data(self.alerts_page.alert_history_datatable)
        enter_text_for_element(self.driver, self.alerts_page.alert_history_search_text, history_table_data)

        filtered_entity_data = self.alerts_page.get_alert_history_entity_data()
        self.assertEqual(history_table_data, filtered_entity_data, "Searched data in alert history not matching")

import django.utils.unittest
if __name__ == '__main__':
    django.utils.unittest.main()
