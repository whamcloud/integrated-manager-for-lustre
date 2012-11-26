from tests.selenium.base import SeleniumBaseTestCase
from tests.selenium.utils.element import select_element_option, get_selected_option_text
from tests.selenium.views.logs import Logs
from tests.selenium.views.servers import Servers

from utils.sample_data import Testdata


class TestLogs(SeleniumBaseTestCase):
    """Test cases for logs page"""
    __test__ = False  # Disabled because these tests are worthless. Need a way to populate these behind the scenes.

    def setUp(self):
        super(TestLogs, self).setUp()

        # Test data for servers
        test_data = Testdata()
        host_list = test_data.get_test_data_for_server_configuration()

        self.navigation.go('Configure', 'Servers')
        servers_page = Servers(self.driver)
        servers_page.add_servers(host_list)

        self.navigation.go('Logs')
        self.logs_page = Logs(self.driver)

    def test_logs_filter(self):
        """Test log filter for particular host"""

        self.logs_page.check_host_list_length()
        select_element_option(self.driver, self.logs_page.log_host_list, 1)
        self.logs_page.log_filter_btn.click()
        host_name = get_selected_option_text(self.driver, self.logs_page.log_host_list)
        self.logs_page.check_table_data()
        host_name_from_table = self.logs_page.get_host_value_from_table_data()
        self.assertEqual(host_name, host_name_from_table)
