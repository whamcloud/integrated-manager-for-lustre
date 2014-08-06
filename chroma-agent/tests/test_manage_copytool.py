import tempfile
import shutil

from mock import patch
from chroma_agent.chroma_common.lib import shell
from tests.command_capture_testcase import CommandCaptureTestCase
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
        super(TestCopytoolManagement, self).setUp()

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
        start_monitored_copytool(self.ct_id)
        self.assertRan(['/sbin/start', 'copytool-monitor',
                        'id=%s' % self.ct_id])

        self.assertRan(['/sbin/start', 'copytool',
                        'ct_arguments=%s' % self.ct_vars['ct_arguments'],
                        'ct_path=%s' % self.ct_bin_path,
                        'id=%s' % self.ct_id])

        self.assertRan(['/sbin/status', 'copytool',
                        'id=%s' % self.ct_id])

    def test_stop_monitored_copytool(self):
        stop_monitored_copytool(self.ct_id)
        self.assertRan(['/sbin/stop', 'copytool',
                        'id=%s' % self.ct_id])

        self.assertRan(['/sbin/stop', 'copytool-monitor',
                        'id=%s' % self.ct_id])

    def test_start_should_be_idempotent(self):
        from chroma_agent.chroma_common.lib.shell import CommandExecutionError

        real_try_run = shell.try_run

        def fake_try_run(*args):
            if args[0][0] == '/sbin/start':
                raise CommandExecutionError(1, args[0],
                                            '', 'Job is already running')
            else:
                real_try_run(*args)

        with patch('chroma_agent.chroma_common.lib.shell.try_run', fake_try_run):
            start_monitored_copytool(self.ct_id)
            self.assertRan(['/sbin/restart', 'copytool-monitor',
                            'id=%s' % self.ct_id])
            self.assertRan(['/sbin/restart', 'copytool',
                            'ct_arguments=%s' % self.ct_vars['ct_arguments'],
                            'ct_path=%s' % self.ct_bin_path,
                            'id=%s' % self.ct_id])

    def test_stop_should_be_idempotent(self):
        from chroma_agent.chroma_common.lib.shell import CommandExecutionError

        def raise_error(obj):
            raise CommandExecutionError(1, [], '', 'Unknown instance')

        with patch('chroma_agent.chroma_common.lib.shell.try_run', side_effect=raise_error):
            stop_monitored_copytool(self.ct_id)

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
