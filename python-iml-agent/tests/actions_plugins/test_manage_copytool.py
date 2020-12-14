import tempfile
import shutil
import mock

from iml_common.test.command_capture_testcase import (
    CommandCaptureTestCase,
    CommandCaptureCommand,
)
from chroma_agent.action_plugins.manage_copytool import (
    start_monitored_copytool,
    stop_monitored_copytool,
    configure_copytool,
    unconfigure_copytool,
    update_copytool,
    list_copytools,
    _copytool_vars,
)
from tests.lib.agent_unit_testcase import AgentUnitTestCase


class TestCopytoolManagement(CommandCaptureTestCase, AgentUnitTestCase):
    def setUp(self):
        super(TestCopytoolManagement, self).setUp()

        from chroma_agent.config_store import ConfigStore

        self.mock_config = ConfigStore(tempfile.mkdtemp())
        mock.patch("chroma_agent.action_plugins.manage_copytool.config", self.mock_config).start()
        mock.patch("chroma_agent.copytool_monitor.config", self.mock_config).start()
        mock.patch("chroma_agent.action_plugins.settings_management.config", self.mock_config).start()

        mock.patch("chroma_agent.action_plugins.manage_copytool._write_service_init").start()

        self.mock_os_remove = mock.MagicMock()
        mock.patch("os.remove", self.mock_os_remove).start()

        from chroma_agent.action_plugins.settings_management import reset_agent_config

        reset_agent_config()

        self.ct_id = "42"
        self.ct_index = 0
        self.ct_archive = 1
        self.ct_bin_path = "/usr/sbin/lhsmtool_foo"
        self.ct_arguments = "-p /archive/testfs"
        self.ct_filesystem = "testfs"
        self.ct_mountpoint = "/mnt/testfs"
        self._configure_copytool()
        self.ct_vars = _copytool_vars(self.ct_id)

        self.addCleanup(mock.patch.stopall)

    def tearDown(self):
        super(TestCopytoolManagement, self).tearDown()

        mock.patch.stopall()

        shutil.rmtree(self.mock_config.path)

    def _configure_copytool(self):
        self.ct_id = configure_copytool(
            self.ct_id,
            self.ct_index,
            self.ct_bin_path,
            self.ct_archive,
            self.ct_filesystem,
            self.ct_mountpoint,
            self.ct_arguments,
        )

    def test_start_monitored_copytool(self):
        self.single_commands(
            CommandCaptureCommand(("systemctl", "daemon-reload")),
            CommandCaptureCommand(
                ("systemctl", "is-active", "chroma-copytool-monitor-%s" % self.ct_id),
                rc=1,
            ),
            CommandCaptureCommand(("systemctl", "start", "chroma-copytool-monitor-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-monitor-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "daemon-reload")),
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-%s" % self.ct_id), rc=1),
            CommandCaptureCommand(("systemctl", "start", "chroma-copytool-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-%s" % self.ct_id)),
        )

        self.assertAgentOK(start_monitored_copytool(self.ct_id))
        self.assertRanAllCommandsInOrder()

    def test_stop_monitored_copytool(self):
        self.single_commands(
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-monitor-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "stop", "chroma-copytool-monitor-%s" % self.ct_id)),
            CommandCaptureCommand(
                ("systemctl", "is-active", "chroma-copytool-monitor-%s" % self.ct_id),
                rc=1,
            ),
            CommandCaptureCommand(("systemctl", "daemon-reload")),
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "stop", "chroma-copytool-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-%s" % self.ct_id), rc=1),
            CommandCaptureCommand(("systemctl", "daemon-reload")),
        )

        with mock.patch("os.path.exists", return_value=True):
            self.assertAgentOK(stop_monitored_copytool(self.ct_id))

        self.assertRanAllCommandsInOrder()
        self.assertEqual(self.mock_os_remove.call_count, 2)
        self.mock_os_remove.assert_called_with("/etc/init.d/chroma-copytool-%s" % self.ct_id)

    def test_start_should_be_idempotent(self):
        self.single_commands(
            CommandCaptureCommand(("systemctl", "daemon-reload")),
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-monitor-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "stop", "chroma-copytool-monitor-%s" % self.ct_id)),
            CommandCaptureCommand(
                ("systemctl", "is-active", "chroma-copytool-monitor-%s" % self.ct_id),
                rc=1,
            ),
            CommandCaptureCommand(("systemctl", "start", "chroma-copytool-monitor-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-monitor-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "daemon-reload")),
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "stop", "chroma-copytool-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-%s" % self.ct_id), rc=1),
            CommandCaptureCommand(("systemctl", "start", "chroma-copytool-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-%s" % self.ct_id)),
        )

        self.assertAgentOK(start_monitored_copytool(self.ct_id))
        self.assertRanAllCommandsInOrder()

    def test_stop_should_be_idempotent1(self):
        self.single_commands(
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-monitor-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "stop", "chroma-copytool-monitor-%s" % self.ct_id)),
            CommandCaptureCommand(
                ("systemctl", "is-active", "chroma-copytool-monitor-%s" % self.ct_id),
                rc=1,
            ),
            CommandCaptureCommand(("systemctl", "daemon-reload")),
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "stop", "chroma-copytool-%s" % self.ct_id)),
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-%s" % self.ct_id), rc=1),
            CommandCaptureCommand(("systemctl", "daemon-reload")),
            CommandCaptureCommand(("systemctl", "daemon-reload")),
            CommandCaptureCommand(("systemctl", "daemon-reload")),
        )

        with mock.patch("os.path.exists", return_value=True):
            self.assertAgentOK(stop_monitored_copytool(self.ct_id))

        with mock.patch("os.path.exists", return_value=False):
            self.assertAgentOK(stop_monitored_copytool(self.ct_id))

        self.assertRanAllCommandsInOrder()

    def test_stop_should_be_idempotent2(self):
        self.single_commands(
            CommandCaptureCommand(
                ("systemctl", "is-active", "chroma-copytool-monitor-%s" % self.ct_id),
                rc=1,
            ),
            CommandCaptureCommand(("systemctl", "daemon-reload")),
            CommandCaptureCommand(("systemctl", "is-active", "chroma-copytool-%s" % self.ct_id), rc=1),
            CommandCaptureCommand(("systemctl", "daemon-reload")),
        )

        with mock.patch("os.path.exists", return_value=True):
            self.assertAgentOK(stop_monitored_copytool(self.ct_id))

        self.assertRanAllCommandsInOrder()

    def test_configure_should_be_idempotent(self):
        expected_kwargs = dict(
            index=self.ct_index,
            bin_path=self.ct_bin_path,
            filesystem=self.ct_filesystem,
            mountpoint=self.ct_mountpoint,
            archive_number=self.ct_archive,
            hsm_arguments=self.ct_arguments,
        )
        with mock.patch("chroma_agent.action_plugins.manage_copytool.update_copytool") as patched_update_copytool:
            self._configure_copytool()
            patched_update_copytool.assert_called_with(self.ct_id, **expected_kwargs)

    @mock.patch("chroma_agent.action_plugins.manage_copytool.stop_monitored_copytool")
    def test_unconfigure_copytool(self, stop_monitored_copytool):
        # NB: configure_copytool is implicitly tested numerous times as
        # part of setUp(). Kind of hacky but whatever.
        unconfigure_copytool(self.ct_id)
        stop_monitored_copytool.assert_called_with(self.ct_id)

    @mock.patch("chroma_agent.action_plugins.manage_copytool.stop_monitored_copytool")
    @mock.patch("chroma_agent.action_plugins.manage_copytool.start_monitored_copytool")
    def test_update_copytool(self, start_monitored_copytool, stop_monitored_copytool):
        update_copytool(self.ct_id, archive_number=2)

        stop_monitored_copytool.assert_called_with(self.ct_id)

        self.assertEquals(self.mock_config.get("copytools", self.ct_id)["archive_number"], 2)

        start_monitored_copytool.assert_called_with(self.ct_id)

    def test_list_copytools(self):
        self.assertDictEqual(list_copytools(), {"raw_result": self.ct_id})
