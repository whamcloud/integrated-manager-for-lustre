import mock
from chroma_agent.lib import node_admin
from chroma_common.lib.util import PlatformInfo
from chroma_common.test.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand


class TestNodeAdmin(CommandCaptureTestCase):
    def setUp(self):
        super(TestNodeAdmin, self).setUp()

        self.write_ifcfg_result = 'bobs.your.uncle'
        self.device_name = 'the device'
        self.mac_address = 'its mac address'

        self.write_ifcfg_mock = mock.patch('chroma_agent.lib.node_admin.write_ifcfg',
                                           return_value=self.write_ifcfg_result).start()

        self.save_platform_info = node_admin.platform_info

        node_admin.platform_info = PlatformInfo('Linux',
                                                'CentOS',
                                                7.2,
                                                '7.21552',
                                                2.7,
                                                7,
                                                '2.6.32-504.12.2.el6.x86_64')

    def tearDown(self):
        super(TestNodeAdmin, self).tearDown()

        node_admin.platform_info = self.save_platform_info

    def test_unmanage_network_nm_running(self):
        self.add_commands(CommandCaptureCommand(('nmcli', 'con', 'load', self.write_ifcfg_result)))

        node_admin.unmanage_network(self.device_name, self.mac_address)

        self.assertRanAllCommandsInOrder()
        self.write_ifcfg_mock.assert_called_with(self.device_name, self.mac_address, None, None)

    def test_unmanage_network_nm_failures(self):
        for expected_rc in [2, 127, 8]:
            self.reset_command_capture()
            self.add_commands(CommandCaptureCommand(('nmcli', 'con', 'load', self.write_ifcfg_result), rc=expected_rc))

            node_admin.unmanage_network(self.device_name, self.mac_address)

            self.assertRanAllCommandsInOrder()
