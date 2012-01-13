""" Create user tests """

import logging

from utils.navigation import Navigation
from views.baselayout import Baselayout
from base import BaseClass

Log = logging.getLogger(__name__)


class Layout(BaseClass):
    def test_01__dashboard_header_and_notification(self):

        # Calling navigation
        navigation_page = Navigation(self.driver)
        navigation_page.click(navigation_page._links['Dashboard'])

        # Calling base_layout
        base_layout_page = Baselayout(self.driver)

        self.assertTrue(base_layout_page.is_logo_head())
        Log.info('Menu header present on dashboard page')

        self.assertTrue(base_layout_page.is_signbtn())
        Log.info('Notification panel present on dashboard  page')

    def test_02__configure_header_and_notification(self):

        # Calling navigation
        navigation_page = Navigation(self.driver)
        navigation_page.click(navigation_page._links['Configure'])

        import time
        time.sleep(10)
        # Calling base_layout
        base_layout_page = Baselayout(self.driver)

        self.assertTrue(base_layout_page.is_logo_head())
        Log.info('Menu header present on configure page')

        self.assertTrue(base_layout_page.is_signbtn())
        Log.info('Notification panel present on configure page')

    def test_03__alerts_header_and_notification(self):

        # Calling navigation
        navigation_page = Navigation(self.driver)
        navigation_page.click(navigation_page._links['Alerts'])

        # Calling base_layout
        base_layout_page = Baselayout(self.driver)

        self.assertTrue(base_layout_page.is_logo_head())
        Log.info('Menu header present on alerts page')

        self.assertTrue(base_layout_page.is_signbtn())
        Log.info('Notification panel present on alerts page')

    def test_04__events_header_and_notification(self):

        # Calling navigation
        navigation_page = Navigation(self.driver)
        navigation_page.click(navigation_page._links['Events'])

        # Calling base_layout
        base_layout_page = Baselayout(self.driver)

        self.assertTrue(base_layout_page.is_logo_head())
        Log.info('Menu header present on events page')

        self.assertTrue(base_layout_page.is_signbtn())
        Log.info('Notification panel present on events page')

    def test_05__logs_header_and_notification(self):

        # Calling navigation
        navigation_page = Navigation(self.driver)
        navigation_page.click(navigation_page._links['Logs'])

        # Calling base_layout
        base_layout_page = Baselayout(self.driver)

        self.assertTrue(base_layout_page.is_logo_head())
        Log.info('Menu header present on logs page')

        self.assertTrue(base_layout_page.is_signbtn())
        Log.info('Notification panel present on logs page')

import unittest
if __name__ == '__main__':
    unittest.main()
