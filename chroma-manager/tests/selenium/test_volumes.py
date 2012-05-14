from views.volumes import Volumes
from base import SeleniumBaseTestCase
from base import wait_for_datatable


class TestVolumes(SeleniumBaseTestCase):
    """Test cases for volume configuration"""

    def setUp(self):
        super(TestVolumes, self).setUp()

        self.navigation.go('Configure', 'Volumes')
        self.volumes_page = Volumes(self.driver)

        wait_for_datatable(self.driver, '#volume_configuration')

    def test_volume_config_error_data(self):
        """Test case for validating volume configuration"""

        # Verifying the volume configuration error dialog being displayed
        self.assertTrue(self.volumes_page.check_volume_config_validation())

    def test_change_volume_config(self):
        """Test for changing volume configuration"""

        # Verifying that volume configuration setting is successful
        self.assertEqual(self.volumes_page.change_volume_config(), 'Update Successful')

import django.utils.unittest
if __name__ == '__main__':
    django.utils.unittest.main()
