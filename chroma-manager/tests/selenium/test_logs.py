from views.logs import Logs
from base import SeleniumBaseTestCase
from base import wait_for_datatable
from base import select_element_option
from base import get_selected_option_text


class TestLogs(SeleniumBaseTestCase):
    """Test cases for logs page"""

    def setUp(self):
        super(TestLogs, self).setUp()

        self.navigation.go('Logs')

        self.logs_page = Logs(self.driver)
        wait_for_datatable(self.driver, '#all_log_content')

    def test_logs_filter(self):
        """Test log filter for particular host"""

        self.logs_page.check_host_list_length()
        select_element_option(self.driver, self.logs_page.log_host_list, 1)
        self.logs_page.log_filter_btn.click()
        host_name = get_selected_option_text(self.driver, self.logs_page.log_host_list)
        self.logs_page.check_table_data()
        host_name_from_table = self.logs_page.get_host_value_from_table_data()
        self.assertEqual(host_name, host_name_from_table)

import django.utils.unittest
if __name__ == '__main__':
    django.utils.unittest.main()
