from tests.selenium.base import SeleniumBaseTestCase
from tests.selenium.views.edit_filesystem import EditFilesystem
from tests.selenium.views.mgt import Mgt
from tests.selenium.views.servers import Servers
from tests.selenium.views.create_filesystem import CreateFilesystem
from tests.selenium.views.volumes import Volumes
from tests.selenium.views.conf_param_dialog import ConfParamDialog
from selenium.common.exceptions import NoSuchElementException
from utils.sample_data import Testdata


class TestCreateFilesystem(SeleniumBaseTestCase):
    """Test cases for file system creation and validations"""

    def setUp(self):
        super(TestCreateFilesystem, self).setUp()

        test_data = Testdata()

        # Test data for file system
        self.filesystem_name = test_data.cluster_data['filesystems']['name']

        # Base filesystem
        self.mgt_volume_name, self.mgt_server_address = self.volume_and_server(0)
        self.mdt_volume_name, self.mdt_server_address = self.volume_and_server(1)
        self.ost_volume_name, self.ost_server_address = self.volume_and_server(2)
        self.mdt_dne_volume_name, self.mdt_dne_server_address = self.volume_and_server(4)

        # Test data for servers
        self.host_list = test_data.get_test_data_for_server_configuration()

        # Pick some volumes
        self.mgt_volume_name, self.mgt_server_address = self.volume_and_server(0)
        self.mdt_volume_name, self.mdt_server_address = self.volume_and_server(1)
        self.ost_volume_name, self.ost_server_address = self.volume_and_server(2)
        self.mdt_dne_volume_name, self.mdt_dne_server_address = self.volume_and_server(4)

        # Add the test servers
        self.navigation.go('Configure', 'Servers')
        self.server_page = Servers(self.driver)
        self.server_page.add_servers(self.host_list)

        # Set our server preferences on the test volumes
        self.navigation.go('Configure', 'Volumes')
        volume_page = Volumes(self.driver)
        for primary_server, volume_name in [
            (self.mgt_server_address, self.mgt_volume_name),
            (self.mdt_server_address, self.mdt_volume_name),
            (self.ost_server_address, self.ost_volume_name)]:
            volume_page.set_primary_server(volume_name, primary_server)

        self.conf_params = test_data.get_test_data_for_conf_params()['filesystem_conf_params']

        self.navigation.go('Configure', 'Filesystems', 'Create_new_filesystem')

    def _check_filesystem_creation(self, more_mdts=[]):
        # Inspect the name and choice of volumes to check they match input
        detail_page = EditFilesystem(self.driver)
        self.assertTrue(detail_page.visible)
        self.assertEqual(detail_page.filesystem_name, self.filesystem_name)
        self.assertEqual(detail_page.mgt_volumes, [[self.mgt_volume_name, self.mgt_server_address]])
        self.assertEqual(detail_page.mdt_volumes, [[self.mdt_volume_name, self.mdt_server_address]] + more_mdts)
        self.assertEqual(detail_page.ost_volumes, [[self.ost_volume_name, self.ost_server_address]])
        return detail_page

    def test_create_filesystem_mgt_separate(self):
        """Create an MGT then filesystem using valid params, check that it
        is created and we are redirected to detail view."""

        # Create MGT
        self.navigation.go('Configure', 'MGTs')
        self.mgt_page = Mgt(self.driver)
        self.mgt_page.create_mgt(self.mgt_server_address, self.mgt_volume_name)

        # Create filesystem
        self.navigation.go('Configure', 'Filesystems', 'Create_new_filesystem')
        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.enter_name(self.filesystem_name)
        create_filesystem_page.select_mgt(self.mgt_server_address)
        create_filesystem_page.select_mdt_volume(self.mdt_server_address, self.mdt_volume_name)
        create_filesystem_page.select_ost_volume(self.ost_server_address, self.ost_volume_name)
        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()

        self._check_filesystem_creation()

    def test_create_filesystem_mgt_inline(self):
        """Create a filesystem and MGT in one operation"""

        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.enter_name(self.filesystem_name)
        create_filesystem_page.select_mgt_volume(self.mgt_server_address, self.mgt_volume_name)
        create_filesystem_page.select_mdt_volume(self.mdt_server_address, self.mdt_volume_name)
        create_filesystem_page.select_ost_volume(self.ost_server_address, self.ost_volume_name)
        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()

        self._check_filesystem_creation()

    def test_create_mdts_dne(self):
        """Test that MDT is validated as present"""
        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.enter_name(self.filesystem_name)
        create_filesystem_page.select_mgt_volume(self.mgt_server_address, self.mgt_volume_name)
        create_filesystem_page.select_mdt_volume(self.mdt_server_address, self.mdt_volume_name)
        create_filesystem_page.toggle_dne()
        create_filesystem_page.select_dne_volume(self.mdt_dne_server_address, self.mdt_dne_volume_name)
        create_filesystem_page.select_ost_volume(self.ost_server_address, self.ost_volume_name)
        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()

        detail_page = self._check_filesystem_creation([[self.mdt_dne_volume_name, self.mdt_dne_server_address]])

        with self.assertRaises(NoSuchElementException):
            try:
                detail_page.mdt_set_state("%s-MDT0000" % self.filesystem_name, "removed")
                detail_page.mdt_set_state("%s-MDT0001" % self.filesystem_name, "removed")
            except NoSuchElementException as e:
                self.assertEqual(e.msg, 'No action found with state removed')
                raise

    def test_name_validation(self):
        """Test that filesystem is validated as non-blank"""

        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.select_mgt_volume(self.mgt_server_address, self.mgt_volume_name)
        create_filesystem_page.select_mdt_volume(self.mdt_server_address, self.mdt_volume_name)
        create_filesystem_page.select_ost_volume(self.ost_server_address, self.ost_volume_name)
        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()
        self.assertEqual(create_filesystem_page.name_error, "File system name is mandatory")

        create_filesystem_page.enter_name(" ")
        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()
        self.assertEqual(create_filesystem_page.name_error, "Name may not contain spaces")

        create_filesystem_page.enter_name(" foo")
        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()
        self.assertEqual(create_filesystem_page.name_error, "Name may not contain spaces")

    def test_mdt_advanced_reset_defaults(self):
        """
        HYD-1401 - Create a filesystem with custome inode_size and bytes_per_inode,
        then check that on returning to the filesystem create page that the default
        advanced MDT config options values have been reset
        """

        # create the mgt seprately to ensure when we test the "reset", that the MGT is
        # no longer selected in the dropdown
        self.navigation.go('Configure', 'MGTs')
        self.mgt_page = Mgt(self.driver)
        self.mgt_page.create_mgt(self.mgt_server_address, self.mgt_volume_name)

        # Create filesystem
        self.navigation.go('Configure', 'Filesystems', 'Create_new_filesystem')
        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.enter_name(self.filesystem_name)
        create_filesystem_page.select_mgt(self.mgt_server_address)
        create_filesystem_page.select_mdt_volume(self.mdt_server_address, self.mdt_volume_name)
        create_filesystem_page.select_ost_volume(self.ost_server_address, self.ost_volume_name)

        # stash the default values for inode_size and bytes_per_inode
        create_filesystem_page.expand_mdt_advanced()
        default_inode_size = create_filesystem_page.mdt_inode_size
        default_bytes_per_inode = create_filesystem_page.mdt_bytes_per_inode

        # now double the default values to create with non-standard sizes
        create_filesystem_page.enter_mdt_inode_size(str(int(default_inode_size) * 2))
        create_filesystem_page.enter_mdt_bytes_per_inode(str(int(default_bytes_per_inode) * 2))

        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()
        self._check_filesystem_creation()

        # go back to filesystem create page and verify that the defaults are back in place
        self.navigation.go('Configure', 'Filesystems', 'Create_new_filesystem')

        # these assertions cover HYD-1502 where the mdt_advanced div show/hide functionality
        # gets out of sync and ends up requiring multiple clicks to show the panel again
        self.assertFalse(create_filesystem_page.mdt_advanced_visible)
        create_filesystem_page.expand_mdt_advanced()
        self.assertTrue(create_filesystem_page.mdt_advanced_visible)

        self.assertEqual(create_filesystem_page.mdt_inode_size, default_inode_size)
        self.assertEqual(create_filesystem_page.mdt_bytes_per_inode, default_bytes_per_inode)
        self.assertEqual(create_filesystem_page.mgt_existing_dropdown_text, '')

    def test_mdt_advanced_validation(self):
        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.enter_name(self.filesystem_name)
        create_filesystem_page.select_mgt_volume(self.mgt_server_address, self.mgt_volume_name)
        create_filesystem_page.select_mdt_volume(self.mdt_server_address, self.mdt_volume_name)
        create_filesystem_page.select_ost_volume(self.ost_server_address, self.ost_volume_name)

        # Enter an invalid value
        create_filesystem_page.expand_mdt_advanced()
        create_filesystem_page.enter_mdt_inode_size('rhubarb')
        create_filesystem_page.collapse_mdt_advanced()

        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()

        self.assertTrue(create_filesystem_page.mdt_advanced_visible)
        self.assertEqual(create_filesystem_page.mdt_inode_size_error, "Must be an integer")
        self.assertEqual(create_filesystem_page.mdt_bytes_per_inode_error, None)

        # Make the other field invalid
        create_filesystem_page.enter_mdt_inode_size('512')
        create_filesystem_page.enter_mdt_bytes_per_inode('rhubarb')

        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()

        self.assertTrue(create_filesystem_page.mdt_advanced_visible)
        self.assertEqual(create_filesystem_page.mdt_inode_size_error, None)
        self.assertEqual(create_filesystem_page.mdt_bytes_per_inode_error, "Must be an integer")

        # Navigate away and back, check the validations are cleared
        self.navigation.go('Configure', 'Servers')
        self.navigation.go('Configure', 'Filesystems', 'Create_new_filesystem')
        create_filesystem_page.expand_mdt_advanced()
        self.assertEqual(create_filesystem_page.mdt_inode_size_error, None)
        self.assertEqual(create_filesystem_page.mdt_bytes_per_inode_error, None)

    def test_mgt_not_selected(self):
        """Test that MGT is validated as present"""

        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.enter_name(self.filesystem_name)
        create_filesystem_page.select_mdt_volume(self.mdt_server_address, self.mdt_volume_name)
        create_filesystem_page.select_ost_volume(self.ost_server_address, self.ost_volume_name)
        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()
        self.assertEqual(create_filesystem_page.mgt_volume_error, "An MGT must be selected")

    def test_mdt_not_selected(self):
        """Test that MDT is validated as present"""

        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.enter_name(self.filesystem_name)
        create_filesystem_page.select_mgt_volume(self.mgt_server_address, self.mgt_volume_name)
        create_filesystem_page.select_ost_volume(self.ost_server_address, self.ost_volume_name)
        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()
        self.assertEqual(create_filesystem_page.mdt_volume_error, "An MDT must be selected")

    def test_invalid_conf_params(self):
        """Test to check whether invalid configuration params are validated"""

        create_filesystem_page = CreateFilesystem(self.driver)
        create_filesystem_page.enter_name(self.filesystem_name)
        create_filesystem_page.select_mgt_volume(self.mgt_server_address, self.mgt_volume_name)
        create_filesystem_page.select_mdt_volume(self.mdt_server_address, self.mdt_volume_name)
        create_filesystem_page.select_ost_volume(self.ost_server_address, self.ost_volume_name)

        create_filesystem_page.open_conf_params()
        conf_params = ConfParamDialog(self.driver)
        conf_params.enter_conf_params({
            'llite.max_cached_mb': 'rhubarb'
        })
        create_filesystem_page.close_conf_params()

        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()

        self.assertEqual(create_filesystem_page.conf_params_open, True)
        self.assertEqual(conf_params.get_conf_param_error('llite.max_cached_mb'), "Invalid size string (must be integer number of m)")

        # Check that if we try again with a different error then the
        # old error goes away and the new one appears
        conf_params.enter_conf_params({
            'llite.max_cached_mb': "",
            'llite.max_read_ahead_mb': "rhubarb"
        })
        create_filesystem_page.close_conf_params()

        create_filesystem_page.create_filesystem_button.click()
        create_filesystem_page.quiesce()

        self.assertEqual(create_filesystem_page.conf_params_open, True)
        self.assertEqual(conf_params.get_conf_param_error('llite.max_cached_mb'), None)
        self.assertEqual(conf_params.get_conf_param_error('llite.max_read_ahead_mb'), "Invalid size string (must be integer number of m)")
