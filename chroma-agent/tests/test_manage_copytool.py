import tempfile
import shutil

from mock import patch
from tests.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand
from chroma_agent.action_plugins.manage_copytool import start_monitored_copytool, stop_monitored_copytool, configure_copytool, unconfigure_copytool, update_copytool, list_copytools, copytool_vars, _copytool_vars


class TestCopytoolManagement(CommandCaptureTestCase):
    def setUp(self):
        super(TestCopytoolManagement, self).setUp()

        from chroma_agent.config_store import ConfigStore
        self.mock_config = ConfigStore(tempfile.mkdtemp())
        patch('chroma_agent.action_plugins.manage_copytool.config',
              self.mock_config).start()
        patch('chroma_agent.copytool_monitor.config',
              self.mock_config).start()
        patch('chroma_agent.action_plugins.settings_management.config',
              self.mock_config).start()

        from chroma_agent.action_plugins.settings_management import reset_agent_config
        reset_agent_config()

        self.ct_id = '42'
        self.ct_index = 0
        self.ct_archive = 1
        self.ct_bin_path = '/usr/sbin/lhsmtool_foo'
        self.ct_arguments = '-p /archive/testfs'
        self.ct_filesystem = 'testfs'
        self.ct_mountpoint = '/mnt/testfs'
        self._configure_copytool()
        self.ct_vars = _copytool_vars(self.ct_id)

        self.addCleanup(patch.stopall)

    def tearDown(self):
        super(TestCopytoolManagement, self).tearDown()

        shutil.rmtree(self.mock_config.path)

    def _configure_copytool(self):
        self.ct_id = configure_copytool(self.ct_id,
                                       self.ct_index,
                                       self.ct_bin_path,
                                       self.ct_archive,
                                       self.ct_filesystem,
                                       self.ct_mountpoint,
                                       self.ct_arguments)

    def test_start_monitored_copytool(self):
        self.add_commands(CommandCaptureCommand(('/sbin/start', 'copytool-monitor', 'id=%s' % self.ct_id)),
                          CommandCaptureCommand(('/sbin/status', 'copytool-monitor', 'id=%s' % self.ct_id)),
                          CommandCaptureCommand(('/sbin/start', 'copytool', 'ct_arguments=%s' % self.ct_vars['ct_arguments'], 'ct_path=%s' % self.ct_bin_path, 'id=%s' % self.ct_id)),
                          CommandCaptureCommand(('/sbin/status', 'copytool', 'id=%s' % self.ct_id)))

        start_monitored_copytool(self.ct_id)

        self.assertRanAllCommandsInOrder()

    def test_stop_monitored_copytool(self):
        run_args = [('/sbin/stop', 'copytool', 'id=%s' % self.ct_id),
                    ('/sbin/stop', 'copytool-monitor', 'id=%s' % self.ct_id)]

        for run_arg in run_args:
            self.add_command(tuple(run_arg))

        stop_monitored_copytool(self.ct_id)

        self.assertRanAllCommandsInOrder()

    def test_start_should_be_idempotent(self):
        self.add_commands(CommandCaptureCommand(('/sbin/start', 'copytool-monitor', 'id=%s' % self.ct_id), rc=1, stdout='/sbin/start', stderr='Job is already running'),
                          CommandCaptureCommand(('/sbin/restart', 'copytool-monitor', 'id=%s' % self.ct_id)),
                          CommandCaptureCommand(('/sbin/status', 'copytool-monitor', 'id=%s' % self.ct_id)),
                          CommandCaptureCommand(('/sbin/start', 'copytool', u'ct_arguments=--quiet --update-interval 5 --event-fifo /var/spool/lhsmtool_foo-testfs-1-0-events --archive 1 -p /archive/testfs /mnt/testfs', u'ct_path=/usr/sbin/lhsmtool_foo', 'id=%s' % self.ct_id)),
                          CommandCaptureCommand(('/sbin/status', 'copytool', 'id=%s' % self.ct_id)))

        start_monitored_copytool(self.ct_id)

        self.assertRanAllCommandsInOrder()

    def test_stop_should_be_idempotent(self):
        self.add_commands(CommandCaptureCommand(('/sbin/stop', 'copytool', 'id=%s' % self.ct_id), rc=1, stderr='Unknown instance'),
                          CommandCaptureCommand(('/sbin/stop', 'copytool-monitor', 'id=%s' % self.ct_id), rc=1, stderr='Unknown instance'))

        stop_monitored_copytool(self.ct_id)

        self.assertRanAllCommandsInOrder()

    def test_configure_should_be_idempotent(self):
        expected_kwargs = dict(
            index = self.ct_index,
            bin_path = self.ct_bin_path,
            filesystem = self.ct_filesystem,
            mountpoint = self.ct_mountpoint,
            archive_number = self.ct_archive,
            hsm_arguments = self.ct_arguments
        )
        with patch('chroma_agent.action_plugins.manage_copytool.update_copytool') as patched_update_copytool:
            self._configure_copytool()
            patched_update_copytool.assert_called_with(self.ct_id, **expected_kwargs)

    @patch('chroma_agent.action_plugins.manage_copytool.stop_monitored_copytool')
    def test_unconfigure_copytool(self, stop_monitored_copytool):
        # NB: configure_copytool is implicitly tested numerous times as
        # part of setUp(). Kind of hacky but whatever.
        unconfigure_copytool(self.ct_id)
        stop_monitored_copytool.assert_called_with(self.ct_id)

    @patch('chroma_agent.action_plugins.manage_copytool.stop_monitored_copytool')
    @patch('chroma_agent.action_plugins.manage_copytool.start_monitored_copytool')
    def test_update_copytool(self, start_monitored_copytool, stop_monitored_copytool):
        update_copytool(self.ct_id, archive_number=2)

        stop_monitored_copytool.assert_called_with(self.ct_id)

        self.assertEquals(self.mock_config.get('copytools', self.ct_id)['archive_number'], 2)

        start_monitored_copytool.assert_called_with(self.ct_id)

    def test_list_copytools(self):
        self.assertDictEqual(list_copytools(), {'raw_result': self.ct_id})

    def test_copytool_vars(self):
        # This is really more a test of @raw_result than anything else...
        result = " ".join(['%s="%s"' % items
                           for items in _copytool_vars(self.ct_id).items()])
        self.assertDictEqual(copytool_vars(self.ct_id),
                             {'raw_result': result})
