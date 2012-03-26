""" Test Events """

from views.events import Events
from utils.constants import Constants
from base import SeleniumBaseTestCase


class TestEvents(SeleniumBaseTestCase):

    def setUp(self):
        super(TestEvents, self).setUp()
        self.navigation.go('Events')
        self.events_page = Events(self.driver)

    def test_events_filter(self):
        if self.events_page.get_host_list_length() > 1:
            self.events_page.select_host(1)
            host_name = self.events_page.get_host_value_from_dropdown()
            self.events_page.filter_records()
            filtered_td_data = self.events_page.get_table_data()
            # Initialise the constants class
            constants = Constants()
            self.NO_DATATABLE_DATA = constants.get_static_text('no_data_for_datable')
            if filtered_td_data == self.NO_DATATABLE_DATA:
                self.assertEqual(filtered_td_data, self.NO_DATATABLE_DATA)
            else:
                self.assertEqual(self.events_page.get_host_value(), host_name)

    def test_events_data(self):
        self.events_page.select_severity(2)
        self.events_page.filter_records()
        event_created_value = self.events_page.get_table_data()
        #Initialise the constants class
        constants = Constants()
        self.NO_DATATABLE_DATA = constants.get_static_text('no_data_for_datable')
        if event_created_value == self.NO_DATATABLE_DATA:
            self.assertEqual(event_created_value, self.NO_DATATABLE_DATA)
        else:
            severity_filter_value = self.events_page.get_severity_value()
            self.assertEqual(severity_filter_value, constants.get_static_text('warning'))

import unittest
if __name__ == '__main__':
    unittest.main()
