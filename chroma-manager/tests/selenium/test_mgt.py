from tests.selenium.views.mgt import Mgt
from tests.selenium.views.servers import Servers
from tests.selenium.base import SeleniumBaseTestCase
from tests.selenium.views.volumes import Volumes
from utils.sample_data import Testdata


class TestMgt(SeleniumBaseTestCase):
    """Test cases for MGT operations"""

    def setUp(self):
        super(TestMgt, self).setUp()

        self.test_data = Testdata()

        # Setup servers and a volume
        self.host_list = self.test_data.get_test_data_for_server_configuration()
        self.navigation.go('Configure', 'Servers')
        self.server_page = Servers(self.driver)
        self.server_page.add_servers(self.host_list)
        self.mgt_volume_name, self.mgt_server_address = self.volume_and_server(0)
        self.navigation.go('Configure', 'Volumes')
        volumes_page = Volumes(self.driver)
        volumes_page.set_primary_server(self.mgt_volume_name, self.mgt_server_address)

        self.navigation.go('Configure', 'MGTs')

    def test_create_mgt(self):
        """Test MGT creation"""

        mgt_page = Mgt(self.driver)
        mgt_page.create_mgt(self.mgt_server_address, self.mgt_volume_name)

        # Check that the created MGT appears in the list
        mgt_page.find_mgt_row(self.mgt_server_address)

    def test_create_button_visibility_without_selecting_storage(self):
        """Check the sensitivity of the create MGT button"""

        mgt_page = Mgt(self.driver)
        self.assertFalse(mgt_page.create_mgt_button.is_enabled())
        mgt_page.select_mgt(self.mgt_server_address, self.mgt_volume_name)
        self.assertTrue(mgt_page.create_mgt_button.is_enabled())

    def test_start_and_stop_mgt(self):
        """Test starting and stopping MGT from the list"""
        mgt_page = Mgt(self.driver)

        mgt_page.create_mgt(self.mgt_server_address, self.mgt_volume_name)
        mgt_page.transition(self.mgt_server_address, 'unmounted')
        mgt_page.transition(self.mgt_server_address, 'mounted')
