from views.events import Events
from utils.constants import static_text
from base import SeleniumBaseTestCase
from base import select_element_option
from base import get_selected_option_text
from base import wait_for_datatable


class TestEvents(SeleniumBaseTestCase):
    """Test cases for events page"""

    def setUp(self):
        super(TestEvents, self).setUp()

        self.navigation.go('Events')
        self.events_page = Events(self.driver)

        wait_for_datatable(self.driver, '#events_table')

    def test_events_filter(self):
        """Test events filter for particular host"""

        self.events_page.check_host_list_length()
        select_element_option(self.driver, self.events_page.host_list, 1)
        host_name = get_selected_option_text(self.driver, self.events_page.host_list)
        self.events_page.filter_btn.click()
        self.events_page.check_table_data()
        self.assertEqual(self.events_page.get_host_value(), host_name)

    def test_events_data(self):
        """Test events filter for particular severity value"""

        self.events_page.check_host_list_length()
        select_element_option(self.driver, self.events_page.event_severity, 2)
        self.events_page.filter_btn.click()
        self.events_page.check_table_data()
        self.assertEqual(self.events_page.get_severity_value(), static_text['warning'])

import django.utils.unittest
if __name__ == '__main__':
    django.utils.unittest.main()
