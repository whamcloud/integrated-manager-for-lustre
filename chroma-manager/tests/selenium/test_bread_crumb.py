from base import SeleniumBaseTestCase
from views.bread_crumb import Breadcrumb
from views.filesystem import Filesystem
from views.servers import Servers
from base import select_element_option
from base import wait_for_element
from base import get_selected_option_text


class TestBreadCrumb(SeleniumBaseTestCase):
    """Test cases for breadcrumb on dashboard page"""

    def setUp(self):
        super(TestBreadCrumb, self).setUp()
        self.navigation.go('Dashboard')

    def test_filesystem_list_length(self):
        """Test for file system list in breadcrumb"""

        self.navigation.go('Configure')
        filesystem_page = Filesystem(self.driver)
        filesystem_list = filesystem_page.get_filesystem_list()

        self.navigation.go('Dashboard')
        self.breadcrumb_page = Breadcrumb(self.driver)
        breadcrumb_filesystem_list = self.breadcrumb_page.get_filesystem_list()

        self.assertListEqual(filesystem_list, breadcrumb_filesystem_list, 'Filesystem list on breadcrumb and filesystem tab do not match')

    def test_server_list_length(self):
        """Test for server list in breadcrumb"""

        self.navigation.go('Configure', 'Servers')
        server_page = Servers(self.driver)
        server_list = server_page.get_server_list()

        self.navigation.go('Dashboard')
        self.breadcrumb_page = Breadcrumb(self.driver)
        select_element_option(self.driver, self.breadcrumb_page.selectView, 1)
        wait_for_element(self.driver, self.breadcrumb_page.serverSelect, 10)
        breadcrumb_server_list = self.breadcrumb_page.get_server_list()

        self.assertListEqual(server_list, breadcrumb_server_list, 'Server list on breadcrumb and server tab do not match')

    def test_unit_change(self):
        """Test for unit list change in breadcrumb"""

        self.breadcrumb_page = Breadcrumb(self.driver)

        select_element_option(self.driver, self.breadcrumb_page.intervalSelect, 1)
        expected_unit_list = self.breadcrumb_page.get_expected_unit_list(get_selected_option_text(self.driver, self.breadcrumb_page.intervalSelect))
        units_list_length = self.breadcrumb_page.get_units_list()
        self.assertListEqual(expected_unit_list, units_list_length, 'Units for "Minutes" time interval do not match')

        select_element_option(self.driver, self.breadcrumb_page.intervalSelect, 2)
        expected_unit_list = self.breadcrumb_page.get_expected_unit_list(get_selected_option_text(self.driver, self.breadcrumb_page.intervalSelect))
        units_list_length = self.breadcrumb_page.get_units_list()
        self.assertListEqual(expected_unit_list, units_list_length, 'Units for "Hour" time interval do not match')

        select_element_option(self.driver, self.breadcrumb_page.intervalSelect, 3)
        expected_unit_list = self.breadcrumb_page.get_expected_unit_list(get_selected_option_text(self.driver, self.breadcrumb_page.intervalSelect))
        units_list_length = self.breadcrumb_page.get_units_list()
        self.assertListEqual(expected_unit_list, units_list_length, 'Units for "Day" time interval do not match')

        select_element_option(self.driver, self.breadcrumb_page.intervalSelect, 4)
        expected_unit_list = self.breadcrumb_page.get_expected_unit_list(get_selected_option_text(self.driver, self.breadcrumb_page.intervalSelect))
        units_list_length = self.breadcrumb_page.get_units_list()
        self.assertListEqual(expected_unit_list, units_list_length, 'Units for "Week" time interval do not match')

import unittest
if __name__ == '__main__':
    unittest.main()
