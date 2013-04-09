#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from selenium.common.exceptions import NoSuchElementException
from testconfig import config
from tests.selenium.base import SeleniumBaseTestCase
from tests.selenium.views.conf_param_dialog import ConfParamDialog
from tests.selenium.views.filesystem import Filesystem
from tests.selenium.views.edit_filesystem import EditFilesystem
from tests.selenium.views.volumes import Volumes

from utils.sample_data import Testdata


class TestEditFilesystem(SeleniumBaseTestCase):
    """Test cases for editing file system"""

    def setUp(self):
        super(TestEditFilesystem, self).setUp()

        test_data = Testdata()

        # Test data for servers
        host_list = test_data.get_test_data_for_server_configuration()

        # Test data for conf params
        self.conf_param_test_data = test_data.get_test_data_for_conf_params()

        # Test data for file system
        self.fs_test_data = test_data.get_test_data_for_filesystem_configuration()
        self.filesystem_name = self.fs_test_data['name']
        self.original_conf_params = self.conf_param_test_data['filesystem_conf_params']

        # Base filesystem
        self.create_filesystem_simple(host_list, self.filesystem_name, self.original_conf_params)

        self.navigation.go('Configure', 'Filesystems')
        fs_page = Filesystem(self.driver)
        fs_page.edit(self.filesystem_name)

        self.edit_filesystem_page = EditFilesystem(self.driver)

    def test_conf_params_for_filesystem(self):
        """Test setting conf params for a filesystem during and after creation"""

        conf_params = self.conf_param_test_data['edit_filesystem_conf_params']

        # Click advanced button
        self.edit_filesystem_page.open_fs_conf_param_dialog()
        dialog = ConfParamDialog(self.driver)

        # Check whether conf param values set during file system creation are displayed correctly
        dialog.check_conf_params(self.original_conf_params)

        # Set new values for conf params
        dialog.set_conf_params(conf_params)
        self.edit_filesystem_page.apply_conf_params()

        # Check that the dialog closed on apply
        self.assertFalse(self.edit_filesystem_page.conf_param_dialog_visible())

        # Check that values persist across a dialog close/open
        self.edit_filesystem_page.open_fs_conf_param_dialog()
        dialog.check_conf_params(conf_params)

        # Check that values persist across a refresh
        self.navigation.refresh()
        self.edit_filesystem_page.open_fs_conf_param_dialog()
        dialog.check_conf_params(conf_params)
        self.edit_filesystem_page.close_conf_params()

    def test_filesystem_conf_param_validation(self):
        invalid_int_string = "Invalid size string (must be integer number of m)"

        # Set an invalid value, check validation message appears
        self.edit_filesystem_page.open_fs_conf_param_dialog()
        dialog = ConfParamDialog(self.driver)
        dialog.set_conf_params({
            'llite.max_cached_mb': "foobar"
        })
        self.edit_filesystem_page.apply_conf_params()
        self.assertTrue(self.edit_filesystem_page.conf_param_dialog_visible())
        dialog.get_conf_param_error('llite.max_cached_mb')

        # Set a different invalid value, check that the dialog stays open, old error cleared, new one present
        dialog.set_conf_params({
            'llite.max_cached_mb': "",
            'llite.max_read_ahead_mb': "foobar",
        })
        self.edit_filesystem_page.apply_conf_params()
        self.assertTrue(self.edit_filesystem_page.conf_param_dialog_visible())
        self.assertEqual(None, dialog.get_conf_param_error('llite.max_cached_mb'))
        self.assertEqual(invalid_int_string, dialog.get_conf_param_error('llite.max_read_ahead_mb'))

        # Navigate away and back, check validation messages are cleared
        self.edit_filesystem_page.close_conf_params()
        self.navigation.go("Configure", "Volumes")
        self.navigation.go('Configure', 'Filesystems')
        fs_page = Filesystem(self.driver)
        fs_page.edit(self.filesystem_name)
        self.edit_filesystem_page.open_fs_conf_param_dialog()
        self.assertTrue(self.edit_filesystem_page.conf_param_dialog_visible())
        self.assertEqual(None, dialog.get_conf_param_error('llite.max_cached_mb'))
        self.assertEqual(None, dialog.get_conf_param_error('llite.max_read_ahead_mb'))

        # Set something with whitespace and check it is trimmed
        dialog.set_conf_params({
            'llite.max_read_ahead_mb': " 10 "
        })
        self.edit_filesystem_page.apply_conf_params()
        self.assertFalse(self.edit_filesystem_page.conf_param_dialog_visible())
        self.edit_filesystem_page.open_fs_conf_param_dialog()
        dialog.check_conf_params({
            'llite.max_read_ahead_mb': "10"
        })

    def test_target_conf_param_validation(self):
        # Click advanced button
        self.edit_filesystem_page.open_target_conf_params('%s-MDT0000' % self.filesystem_name)
        dialog = ConfParamDialog(self.driver)

        # Set new values for conf params
        dialog.set_conf_params({
            'lov.qos_prio_free': "rhubarb"
        })
        self.edit_filesystem_page.apply_target_conf_params()

        # Check that the dialog stays open
        expected = "Must be an integer between 0 and 100"
        self.assertEqual(expected, dialog.get_conf_param_error('lov.qos_prio_free'))

    def _test_conf_params_for_target(self, target_name, conf_params):
        # Click target element to open and set conf params
        self.edit_filesystem_page.open_target_conf_params(target_name)
        dialog = ConfParamDialog(self.driver)
        dialog.set_conf_params(conf_params)

        # Click Apply button
        self.edit_filesystem_page.apply_target_conf_params()
        self.edit_filesystem_page.close_target_conf_params()

        self.assertFalse(self.edit_filesystem_page.conf_param_dialog_visible())

        # Re-open dialog and check params are present
        self.edit_filesystem_page.open_target_conf_params(target_name)

        dialog.check_conf_params(conf_params)
        self.edit_filesystem_page.close_target_conf_params()

        # Check params are preserved across a refresh
        self.navigation.refresh()
        self.edit_filesystem_page.open_target_conf_params(target_name)
        dialog.check_conf_params(conf_params)
        self.edit_filesystem_page.close_target_conf_params()

    def test_conf_params_for_mdt(self):
        """
        Test that conf params may be set for an MDT from the filesystem detail view
        """

        mdt_conf_params = self.conf_param_test_data['mdt_conf_params']
        self._test_conf_params_for_target('%s-MDT0000' % self.filesystem_name, mdt_conf_params)

    def test_conf_params_for_ost(self):
        """
        Test that conf params may be set for an OST from the filesystem detail view
        """

        ost_conf_params = self.conf_param_test_data['ost_conf_params']
        self._test_conf_params_for_target('%s-OST0000' % self.filesystem_name, ost_conf_params)

    def add_osts_and_verify(self, volumes, ost_index_base):
        """
        Add many OSTs, given that the filesystem detail page is rendered
        """

        # Check that the OSTs don't already exist
        osts_to_create = ["%s-OST%04d" % (self.filesystem_name, ost_index) for ost_index in range(ost_index_base, ost_index_base + len(volumes))]
        for link_text in osts_to_create:
            with self.assertRaises(NoSuchElementException):
                self.driver.find_element_by_link_text(link_text)

        self.edit_filesystem_page.add_osts(volumes)

        # Check that the new OSTs are on the page
        for link_text in osts_to_create:
            self.driver.find_element_by_link_text(link_text)

    def remove_ost_and_verify(self, ost_index):
        """
        Remove an OST - may only be run when on the filesystem detail page already.
        Also asserts the OST label is removed after completion of removal
        """
        link_text = "%s-OST%04d" % (self.filesystem_name, ost_index)
        self.edit_filesystem_page.ost_set_state(link_text, "removed")
        with self.assertRaises(NoSuchElementException):
            self.driver.find_element_by_link_text(link_text)

    def prepare_volume_for_use(self, volume_and_server_index):
        """
        Quickie helper to set the primary server for a volume prior to being
        allocated as a target. Must be done before being used as the primary server
        is selected at random at runtime
        """
        # Go to the Volumes page and set up a volume
        volume_name, server_address = self.volume_and_server(volume_and_server_index)
        self.navigation.go('Configure', 'Volumes')
        volume_page = Volumes(self.driver)
        volume_page.set_primary_server(volume_name, server_address)

        # Go back to the filesystem detail page
        self.navigation.go('Configure', 'Filesystems')
        fs_page = Filesystem(self.driver)
        fs_page.edit(self.filesystem_name)
        return server_address, volume_name

    def test_add_osts(self):
        """
        Test adding multiple OSTs at once
        """
        self.assertGreaterEqual(len(config['volumes']), 5)
        # Prepare two new volumes
        volumes = [self.prepare_volume_for_use(3 + i) for i in range(0, 2)]

        # Check that adding an OST causes the new OST to be shown in the filesystem details
        self.add_osts_and_verify(volumes, ost_index_base=1)

    # HYD-1403 for testing HYD-1309 - removed OST not available to re-add
    def test_adding_removed_ost(self):
        # prep a new volume
        # create server uses indices 0 through 2 for the base filesystem
        new_ost_server_address, new_ost_volume_name = self.prepare_volume_for_use(3)

        # do a cycle of add, remove, add without a page refresh
        self.add_osts_and_verify([(new_ost_server_address, new_ost_volume_name)], ost_index_base=1)
        self.remove_ost_and_verify(ost_index=1)
        self.add_osts_and_verify([(new_ost_server_address, new_ost_volume_name)], ost_index_base=2)

    def test_stop_start_ost(self):
        self.edit_filesystem_page.ost_set_state("%s-OST0000" % self.filesystem_name, "unmounted")
        self.edit_filesystem_page.ost_set_state("%s-OST0000" % self.filesystem_name, "mounted")

    def test_remove_ost(self):
        self.remove_ost_and_verify(ost_index=0)

    def test_remove_filesystem(self):
        """Test that when removing a filesystem from it's detail page, we are
        sent to the filesystem list view after completion"""
        self.edit_filesystem_page.set_state('removed')
        list_view = Filesystem(self.driver)
        self.assertTrue(list_view.visible)

    def test_stop_start_mdt(self):
        self.edit_filesystem_page.mdt_set_state("%s-MDT0000" % self.filesystem_name, "unmounted")
        self.edit_filesystem_page.mdt_set_state("%s-MDT0000" % self.filesystem_name, "mounted")

    def test_stop_start_mgt(self):
        self.edit_filesystem_page.mgt_set_state("MGS", "unmounted")
        self.edit_filesystem_page.mgt_set_state("MGS", "mounted")
