""" Test Logs """

from views.logs import Logs
from utils.constants import Constants
from base import SeleniumBaseTestCase

from base import wait_for_datatable


class TestLogs(SeleniumBaseTestCase):
    def setUp(self):
        super(TestLogs, self).setUp()
        self.navigation.go('Logs')
        self.logs_page = Logs(self.driver)
        wait_for_datatable(self.driver, '#all_log_content')
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
