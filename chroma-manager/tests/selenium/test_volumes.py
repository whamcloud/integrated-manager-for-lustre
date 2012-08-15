from tests.selenium.views.servers import Servers
from tests.selenium.views.volumes import Volumes
from tests.selenium.base import SeleniumBaseTestCase

from utils.sample_data import Testdata


class TestVolumes(SeleniumBaseTestCase):
    """Test cases for volume configuration"""

    def setUp(self):
        super(TestVolumes, self).setUp()

        # Test data for servers
        test_data = Testdata()
        host_list = test_data.get_test_data_for_server_configuration()

        self.navigation.go('Configure', 'Servers')
        self.servers_page = Servers(self.driver)
        self.servers_page.add_servers(host_list)

        self.navigation.go('Configure', 'Volumes')
        self.volumes_page = Volumes(self.driver)

    def test_volume_config_error_data(self):
        """Test case for validating volume configuration"""

        # Verifying the volume configuration error dialog being displayed
        self.assertTrue(self.volumes_page.check_volume_config_validation())

    def test_change_volume_config(self):
        """Test for changing volume configuration"""

        # Verifying that volume configuration setting is successful
        self.assertTrue(self.volumes_page.change_volume_config())
