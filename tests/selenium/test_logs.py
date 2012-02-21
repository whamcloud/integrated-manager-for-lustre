""" Test Logs """

from utils.navigation import Navigation
from views.logs import Logs
from utils.constants import Constants
from base import SeleniumBaseTestCase


class TestLogs(SeleniumBaseTestCase):
    def setUp(self):
        super(TestLogs, self).setUp()
        # Calling navigation
        self.page_navigation = Navigation(self.driver)
        self.fpage_navigation.click(self.page_navigation.links['Logs'])
        # Calling base_layout
        self.logs_page = Logs(self.driver)
        self.table_data = self.logs_page.get_table_data()

    def test_logs_filter(self):
        if self.logs_page.get_host_list_length() > 1:
            #selecting first host name from the host list
            self.logs_page.click_log_host_list(1)
            self.logs_page.click_filter()
            host_name_from_dropdown = self.logs_page.get_host_value_from_dropdown()
            # Initialise the constants class
            constants = Constants()
            self.NO_DATATABLE_DATA = constants.get_static_text('no_data_for_datable')
            if self.table_data == self.NO_DATATABLE_DATA:
                self.assertEqual(self.table_data, self.NO_DATATABLE_DATA)
            else:
                host_name_from_table = self.logs_page.get_host_value_from_table_data()
                self.assertEqual(host_name_from_dropdown, host_name_from_table)

import unittest
if __name__ == '__main__':
    unittest.main()
