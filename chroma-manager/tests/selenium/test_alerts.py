from tests.selenium.views.alerts import Alerts
from tests.selenium.base import SeleniumBaseTestCase
from tests.selenium.base import enter_text_for_element


class TestAlerts(SeleniumBaseTestCase):
    """Test cases for alerts page"""
    __test__ = False  # Disabled because these tests are worthless. Need a way to populate these behind the scenes.

    def setUp(self):
        super(TestAlerts, self).setUp()

        self.navigation.go('Alerts')
        self.alerts_page = Alerts(self.driver)

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
