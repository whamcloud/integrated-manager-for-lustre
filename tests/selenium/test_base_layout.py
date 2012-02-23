""" Test Base Layout """

import logging

from utils.navigation import Navigation
from views.base_layout import Baselayout
from base import SeleniumBaseTestCase

Log = logging.getLogger(__name__)


class Layout(SeleniumBaseTestCase):
    def test_dashboard_header_and_notification(self):

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Dashboard'])

        # Calling base_layout
        base_page_layout = Baselayout(self.driver)

        self.assertTrue(base_page_layout.logo_head_displayed())
        Log.info('Menu header present on dashboard page')

        base_page_layout.open_sidebar()
        self.assertTrue(base_page_layout.sidebar_displayed())
        Log.info('Notification panel present on dashboard  page')

    def test_configure_header_and_notification(self):

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Configure'])

        # FIXME: need to add a generic function to wait for an action
        import time
        time.sleep(5)
        # Calling base_layout
        base_page_layout = Baselayout(self.driver)

        self.assertTrue(base_page_layout.logo_head_displayed())
        Log.info('Menu header present on configure page')

        base_page_layout.open_sidebar()
        self.assertTrue(base_page_layout.sidebar_displayed())
        Log.info('Notification panel present on configure page')

    def test_alerts_header_and_notification(self):

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Alerts'])

        # Calling base_layout
        base_page_layout = Baselayout(self.driver)

        self.assertTrue(base_page_layout.logo_head_displayed())
        Log.info('Menu header present on alerts page')

        base_page_layout.open_sidebar()
        self.assertTrue(base_page_layout.sidebar_displayed())
        Log.info('Notification panel present on alerts page')

    def test_events_header_and_notification(self):

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Events'])

        # Calling base_layout
        base_page_layout = Baselayout(self.driver)

        self.assertTrue(base_page_layout.logo_head_displayed())
        Log.info('Menu header present on events page')

        base_page_layout.open_sidebar()
        self.assertTrue(base_page_layout.sidebar_displayed())
        Log.info('Notification panel present on events page')

    def test_logs_header_and_notification(self):

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation.links['Logs'])

        # Calling base_layout
        base_page_layout = Baselayout(self.driver)

        self.assertTrue(base_page_layout.logo_head_displayed())
        Log.info('Menu header present on logs page')

        base_page_layout.open_sidebar()
        self.assertTrue(base_page_layout.sidebar_displayed())
        Log.info('Notification panel present on logs page')

import unittest
if __name__ == '__main__':
    unittest.main()
