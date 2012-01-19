""" Test Events """

from utils.navigation import Navigation
from views.events import Events
from utils.constants import Constants
from base import SeleniumBaseTestCase


class Alertsdata(SeleniumBaseTestCase):

    def test_events_filter(self):

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation._links['Events'])

        # Calling base_layout
        alerts_page = Events(self.driver)

        td_data = alerts_page.get_table_data()

        alerts_page.click_filter()

        filtered_td_data = alerts_page.get_table_data()

        # Initialise the constants class
        constants = Constants()
        self.NO_DATATABLE_DATA = constants.get_static_text('no_data_for_datable')

        if td_data == self.NO_DATATABLE_DATA:
            self.assertEqual(filtered_td_data, self.NO_DATATABLE_DATA)
        else:
            self.assertNotEqual(filtered_td_data, self.NO_DATATABLE_DATA)

    def test_events_data(self):

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation._links['Events'])

        # Calling base_layout
        alerts_page = Events(self.driver)

        alerts_page.click_severity_select(2)

        alerts_page.click_filter()

        event_created_value = alerts_page.get_table_data()

        #Initialise the constants class
        constants = Constants()
        self.NO_DATATABLE_DATA = constants.get_static_text('no_data_for_datable')

        if event_created_value == self.NO_DATATABLE_DATA:
            self.assertEqual(event_created_value, self.NO_DATATABLE_DATA)
        else:
            severity_filter_value = alerts_page.get_severity_value()
            self.assertEqual(severity_filter_value, 'warning')

import unittest
if __name__ == '__main__':
    unittest.main()
