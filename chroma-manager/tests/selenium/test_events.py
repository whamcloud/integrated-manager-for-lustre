from tests.selenium.base import SeleniumBaseTestCase
from tests.selenium.views.events import Events
from tests.selenium.views.servers import Servers
from tests.selenium.utils.constants import static_text
from tests.selenium.utils.element import select_element_option, get_selected_option_text

from utils.sample_data import Testdata


class TestEvents(SeleniumBaseTestCase):
    """Test cases for events page"""
    __test__ = False  # Disabled because these tests are worthless. Need a way to populate these behind the scenes.

    def setUp(self):
        super(TestEvents, self).setUp()

        test_data = Testdata()
        host_list = test_data.get_test_data_for_server_configuration()

        self.navigation.go('Configure', 'Servers')
        server_page = Servers(self.driver)
        server_page.add_servers(host_list)

        self.navigation.go('Events')
        self.events_page = Events(self.driver)

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
