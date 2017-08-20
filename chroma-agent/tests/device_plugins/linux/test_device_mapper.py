from tests.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand
from chroma_agent.device_plugins.linux_components.device_mapper import DmsetupTable


class TestDmsetupTable(CommandCaptureTestCase):

    def test_lvm2_not_installed(self):
        self.add_commands(CommandCaptureCommand(('vgs', '--units', 'b', '--noheadings', '-o', 'vg_name,vg_uuid,vg_size'),
                                                rc=self.CommandNotFound),
                          CommandCaptureCommand(('dmsetup', 'table'),
                                                stdout="No devices found"))

        dm_setup_table = DmsetupTable({})

        self.assertEqual(dm_setup_table.vgs, {})
        self.assertEqual(dm_setup_table.lvs, {})

        self.assertRanAllCommandsInOrder()

        self.reset_command_capture()
        self.add_commands(CommandCaptureCommand(('vgs', '--units', 'b', '--noheadings', '-o', 'vg_name,vg_uuid,vg_size'),
                                                rc=self.CommandNotFound),
                          CommandCaptureCommand(('lvs', '--units', 'b', '--noheadings', '-o', 'lv_name,lv_uuid,lv_size,lv_path', 'bob'),
                                                rc=self.CommandNotFound))

        for vgs in dm_setup_table._get_vgs():
            self.assertFalse(True, '_get_vgs did not deal with missing vgs')

        for lvs in dm_setup_table._get_lvs('bob'):
            self.assertFalse(True, '_get_lvs did not deal with missing lvg')

        self.assertRanAllCommandsInOrder()
