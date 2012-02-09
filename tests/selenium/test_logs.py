""" Test Logs """

from utils.navigation import Navigation
from views.logs import Logs
from utils.constants import Constants
from base import SeleniumBaseTestCase


class Logsdata(SeleniumBaseTestCase):

    def test_logs_filter(self):

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Logs'])

        # Calling base_layout
        logs_page = Logs(self.driver)

        if logs_page.get_host_list_length() > 1:
            #selecting first host name from the host list
            logs_page.click_log_host_list(1)

            logs_page.click_filter()

            table_data = logs_page.get_table_data()

            host_name_from_dropdown = logs_page.get_host_value_from_dropdown()

            # Initialise the constants class
            constants = Constants()
            self.NO_DATATABLE_DATA = constants.get_static_text('no_data_for_datable')

            if table_data == self.NO_DATATABLE_DATA:
                self.assertEqual(table_data, self.NO_DATATABLE_DATA)
            else:
                host_name_from_table = logs_page.get_host_value_from_table_data()
                self.assertEqual(host_name_from_dropdown, host_name_from_table)

import unittest
if __name__ == '__main__':
    unittest.main()
