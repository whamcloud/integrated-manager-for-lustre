""" Test Base Layout """

import django.utils.unittest

from views.base_layout import Baselayout
from base import SeleniumBaseTestCase
from base import wait_for_element


class TestBaseLayout(SeleniumBaseTestCase):

    base_page_layout = None
    vertical_side_bar = None
    pages = None
    sidebar_close = None

    def setUp(self):
        super(TestBaseLayout, self).setUp()
        self.base_page_layout = Baselayout(self.driver)
        self.vertical_side_bar = self.base_page_layout.vertical_sidebar_css
        self.pages = self.base_page_layout.navigation_pages
        self.sidebar_close = self.base_page_layout.sidebar_close

    def test_all_pages(self):
        for page in self.pages:
            self.check_base_page_layout(page)

    def check_base_page_layout(self, page):
        self.test_logger.info('Testing Page:' + page)
        self.navigation.go(page)
        for menu_selector in self.base_page_layout.menu_element_ids:
            self.assertTrue(wait_for_element(self.driver, menu_selector, 10), 'Menu with element id:' + menu_selector + ' is missing on page: ' + page)

        for image_selector in self.base_page_layout.image_element_css:
            self.assertTrue(wait_for_element(self.driver, image_selector, 10), 'Image with element id:' + image_selector + ' is missing on page: ' + page)

        self.open_slider_check(page)

    def open_slider_check(self, page):
        self.vertical_side_bar.click()
        self.assertTrue(wait_for_element(self.driver, self.base_page_layout.sidebar_id, 10), 'Unable to open Notification side bar with id:' + self.base_page_layout.sidebar_id + ' on page:' + page)
        self.sidebar_close.click()

if __name__ == '__main__':
    django.utils.unittest.main()
