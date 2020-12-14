import errno
import mock
from chroma_agent.lib import node_admin
from chroma_agent.lib.shell import AgentShell
from iml_common.test.command_capture_testcase import (
    CommandCaptureTestCase,
    CommandCaptureCommand,
)


class TestNodeAdmin(CommandCaptureTestCase):
    def setUp(self):
        super(TestNodeAdmin, self).setUp()

        self.write_ifcfg_result = "bobs.your.uncle"
        self.device_name = "the device"
        self.mac_address = "its mac address"

        self.write_ifcfg_mock = mock.patch(
            "chroma_agent.lib.node_admin.write_ifcfg",
            return_value=self.write_ifcfg_result,
        ).start()

    def test_unmanage_network_nm_running(self):
        self.add_commands(CommandCaptureCommand(("nmcli", "con", "load", self.write_ifcfg_result)))

        node_admin.unmanage_network(self.device_name, self.mac_address)

        self.assertRanAllCommandsInOrder()
        self.write_ifcfg_mock.assert_called_with(self.device_name, self.mac_address, None, None)

    def test_unmanage_network_nm_permission_denied(self):
        noent_exception = OSError()
        noent_exception.errno = errno.EACCES

        with mock.patch("chroma_agent.lib.shell.AgentShell.try_run", side_effect=noent_exception):
            with self.assertRaises(OSError):
                self.assertIsNone(node_admin.unmanage_network(self.device_name, self.mac_address))

    def test_unmanage_network_nm_not_installed(self):
        noent_exception = OSError()
        noent_exception.errno = errno.ENOENT

        with mock.patch("chroma_agent.lib.shell.AgentShell.try_run", side_effect=noent_exception):
            self.assertIsNone(node_admin.unmanage_network(self.device_name, self.mac_address))

    def test_unmanage_network_nm_known_failures(self):
        for expected_rc in [node_admin.NM_STOPPED_RC]:
            self.reset_command_capture()
            self.add_commands(CommandCaptureCommand(("nmcli", "con", "load", self.write_ifcfg_result), rc=expected_rc))

            node_admin.unmanage_network(self.device_name, self.mac_address)

            self.assertRanAllCommandsInOrder()

    def test_unmanage_network_nm_unknown_failures(self):
        for expected_rc in [
            2,
            127,
        ]:  # Network Manager bad syntax and command unavailable return codes
            self.reset_command_capture()
            self.add_commands(CommandCaptureCommand(("nmcli", "con", "load", self.write_ifcfg_result), rc=expected_rc))

            with self.assertRaises(AgentShell.CommandExecutionError):
                node_admin.unmanage_network(self.device_name, self.mac_address)

            self.assertRanAllCommandsInOrder()
