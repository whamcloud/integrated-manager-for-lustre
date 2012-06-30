from tests.selenium.views.volumes import Volumes
from tests.selenium.base import SeleniumBaseTestCase


class TestVolumes(SeleniumBaseTestCase):
    """Test cases for volume configuration"""

    def setUp(self):
        super(TestVolumes, self).setUp()

        self.navigation.go('Configure', 'Volumes')
        self.volumes_page = Volumes(self.driver)

    def test_volume_config_error_data(self):
        """Test case for validating volume configuration"""

        # Verifying the volume configuration error dialog being displayed
        self.assertTrue(self.volumes_page.check_volume_config_validation())

    def test_change_volume_config(self):
        """Test for changing volume configuration"""

        # Verifying that volume configuration setting is successful
        self.assertEqual(self.volumes_page.change_volume_config(), 'Update Successful')
