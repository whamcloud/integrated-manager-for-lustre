""" Test Base Layout """

from base import SeleniumBaseTestCase
from views.bread_crumb import Breadcrumb
from views.filesystem import Filesystem
from views.servers import Servers


class TestBreadCrumb(SeleniumBaseTestCase):
    def test_filesystem_list_length(self):
        self.navigation.go('Configure')

        filesystem_page = Filesystem(self.driver)
        filesystem_list_length = filesystem_page.get_file_system_list_length()

        self.navigation.go('Dashboard')
        self.breadcrumb_page = Breadcrumb(self.driver)

        breadcrumb_filesystem_list_length = self.breadcrumb_page.get_filesystem_list_length()

        self.assertEqual(filesystem_list_length, breadcrumb_filesystem_list_length, 'Filesystem list on breadcrumb and filesystem tab do not match')

    def test_server_list_length(self):
        self.navigation.go('Configure', 'Servers')

        create_server_page = Servers(self.driver)
        server_list_length = create_server_page.get_server_list_length()

        self.navigation.go('Dashboard')
        self.breadcrumb_page = Breadcrumb(self.driver)

        self.breadcrumb_page.select_view(1)

        breadcrumb_server_list_length = self.breadcrumb_page.server_list_length()

        self.assertEqual(server_list_length, breadcrumb_server_list_length, 'Server list on breadcrumb and server tab do not match')

    def test_unit_change(self):
        self.navigation.go('Dashboard')
        self.breadcrumb_page = Breadcrumb(self.driver)

        self.breadcrumb_page.select_time_interval(1)
        units_list_length = self.breadcrumb_page.get_unit_list_length()
        self.assertEqual(60, units_list_length, 'Units for "Minutes" time interval do not match')

        self.breadcrumb_page.select_time_interval(2)
        units_list_length = self.breadcrumb_page.get_unit_list_length()
        self.assertEqual(23, units_list_length, 'Units for "Hour" time interval do not match')

        self.breadcrumb_page.select_time_interval(3)
        units_list_length = self.breadcrumb_page.get_unit_list_length()
        self.assertEqual(31, units_list_length, 'Units for "Day" time interval do not match')

        self.breadcrumb_page.select_time_interval(4)
        units_list_length = self.breadcrumb_page.get_unit_list_length()
        self.assertEqual(4, units_list_length, 'Units for "Week" time interval do not match')

import unittest
if __name__ == '__main__':
    unittest.main()
