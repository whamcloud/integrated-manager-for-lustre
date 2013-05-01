from tests.selenium.views.filesystem import Filesystem
from tests.selenium.base import SeleniumBaseTestCase
from utils.sample_data import Testdata


class TestFilesystem(SeleniumBaseTestCase):
    """Test cases for file system related operations"""

    def setUp(self):
        super(TestFilesystem, self).setUp()

        self.test_data = Testdata()
        self.host_list = self.test_data.get_test_data_for_server_configuration()
        self.fs_test_data = self.test_data.get_test_data_for_filesystem_configuration()
        self.filesystem_name = self.fs_test_data['name']

        self.create_filesystem_simple(self.host_list, self.filesystem_name)

        self.navigation.go('Configure', 'Filesystems')

    def test_filesystem_start_and_stop(self):
        """Test for starting and stopping file system"""

        fs_page = Filesystem(self.driver)

        fs_page.transition(self.filesystem_name, 'stopped')

        fs_page.transition(self.filesystem_name, 'available')
