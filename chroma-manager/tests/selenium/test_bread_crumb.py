from tests.selenium.base import SeleniumBaseTestCase
from tests.selenium.utils.sample_data import Testdata
from tests.selenium.views.bread_crumb import Breadcrumb
from tests.selenium.views.filesystem import Filesystem
from tests.selenium.views.servers import Servers
from tests.selenium.utils.element import (
    select_element_option, get_selected_option_text,
    wait_for_element_by_css_selector
)


class TestBreadCrumb(SeleniumBaseTestCase):
    """Test cases for breadcrumb on dashboard page"""

    def setUp(self):
        super(TestBreadCrumb, self).setUp()
        self.test_data = Testdata()
        self.navigation.go('Dashboard')

    def test_filesystem_list_length(self):
        """Test for file system list in breadcrumb"""

        # Verify empty with no filesystems.
        self.navigation.go('Configure')
        filesystem_page = Filesystem(self.driver)
        filesystem_list = filesystem_page.get_filesystem_list()

        self.navigation.go('Dashboard')
        self.breadcrumb_page = Breadcrumb(self.driver)
        breadcrumb_filesystem_list = self.breadcrumb_page.get_filesystem_list()

        self.assertListEqual(filesystem_list, breadcrumb_filesystem_list, 'Filesystem list on breadcrumb and filesystem tab do not match')

        # Verify length is 1 with one filesystem.
        self.navigation.go('Configure')
        filesystem_page = Filesystem(self.driver)
        self.create_filesystem_simple(
            self.test_data.get_test_data_for_server_configuration(),
            self.test_data.get_test_data_for_filesystem_configuration()['name'],
            self.test_data.get_test_data_for_conf_params()['filesystem_conf_params']
        )
        filesystem_list = filesystem_page.get_filesystem_list()

        self.navigation.go('Dashboard')
        self.breadcrumb_page = Breadcrumb(self.driver)
        breadcrumb_filesystem_list = self.breadcrumb_page.get_filesystem_list()

        self.assertListEqual(filesystem_list, breadcrumb_filesystem_list, 'Filesystem list on breadcrumb and filesystem tab do not match')

    def test_server_list_length(self):
        """Test for server list in breadcrumb"""

        self.navigation.go('Configure', 'Servers')
        server_page = Servers(self.driver)
        server_page.add_servers(self.test_data.get_test_data_for_server_configuration())
        server_list = server_page.get_server_list()

        self.navigation.go('Dashboard')
        self.breadcrumb_page = Breadcrumb(self.driver)
        select_element_option(self.driver, self.breadcrumb_page.selectView, 1)
        wait_for_element_by_css_selector(self.driver, self.breadcrumb_page.serverSelect, 10)
        breadcrumb_server_list = self.breadcrumb_page.get_server_list()

        self.assertListEqual(server_list, breadcrumb_server_list, 'Server list on breadcrumb and server tab do not match')

    def test_unit_change(self):
        """Test for unit list change in breadcrumb"""

        self.breadcrumb_page = Breadcrumb(self.driver)

        select_element_option(self.driver, self.breadcrumb_page.intervalSelect, 0)
        expected_units_list = self.breadcrumb_page.get_expected_units_list(get_selected_option_text(self.driver, self.breadcrumb_page.intervalSelect))
        actual_units_list = self.breadcrumb_page.get_units_list()
        self.assertListEqual(expected_units_list, actual_units_list, 'Units for "Minutes" time interval do not match: Actual[%s] Expected[%s]' % (actual_units_list, expected_units_list))

        select_element_option(self.driver, self.breadcrumb_page.intervalSelect, 1)
        expected_units_list = self.breadcrumb_page.get_expected_units_list(get_selected_option_text(self.driver, self.breadcrumb_page.intervalSelect))
        actual_units_list = self.breadcrumb_page.get_units_list()
        self.assertListEqual(expected_units_list, actual_units_list, 'Units for "Hour" time interval do not match')

        select_element_option(self.driver, self.breadcrumb_page.intervalSelect, 2)
        expected_units_list = self.breadcrumb_page.get_expected_units_list(get_selected_option_text(self.driver, self.breadcrumb_page.intervalSelect))
        actual_units_list = self.breadcrumb_page.get_units_list()
        self.assertListEqual(expected_units_list, actual_units_list, 'Units for "Day" time interval do not match')

        select_element_option(self.driver, self.breadcrumb_page.intervalSelect, 3)
        expected_units_list = self.breadcrumb_page.get_expected_units_list(get_selected_option_text(self.driver, self.breadcrumb_page.intervalSelect))
        actual_units_list = self.breadcrumb_page.get_units_list()
        self.assertListEqual(expected_units_list, actual_units_list, 'Units for "Week" time interval do not match')
