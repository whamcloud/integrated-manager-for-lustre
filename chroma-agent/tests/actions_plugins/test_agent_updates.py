import mock
import os
from tempfile import NamedTemporaryFile

from mock import patch

from chroma_agent.action_plugins import agent_updates
from chroma_agent.device_plugins import lustre
from chroma_agent import config
from tests.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand
from chroma_agent.chroma_common.lib.agent_rpc import agent_result, agent_result_ok, agent_error


class TestManageUpdates(CommandCaptureTestCase):
    def setUp(self):
        super(TestManageUpdates, self).setUp()
        self.tmpRepo = NamedTemporaryFile(delete=False)

        self.old_scan_packages = lustre.scan_packages
        lustre.scan_packages = mock.Mock(return_value={})

    def tearDown(self):
        if os.path.exists(self.tmpRepo.name):
            os.remove(self.tmpRepo.name)

        lustre.scan_packages = self.old_scan_packages

    def test_configure_repo(self):
        import chroma_agent
        expected_content = """
[Intel-Lustre-Manager]
name=Intel Lustre Manager updates
baseurl=http://www.test.com/test.repo
enabled=1
gpgcheck=0
sslverify = 1
sslcacert = /var/lib/chroma/authority.crt
sslclientkey = /var/lib/chroma/private.pem
sslclientcert = /var/lib/chroma/self.crt
"""
        provided_content = """
[Intel-Lustre-Manager]
name=Intel Lustre Manager updates
baseurl=http://www.test.com/test.repo
enabled=1
gpgcheck=0
sslverify = 1
sslcacert = {0}
sslclientkey = {1}
sslclientcert = {2}
"""
        with patch('os.rename', create=True) as mock_rename:
            with patch('os.open', create=True):
                with patch('os.fdopen', spec=file, create=True) as mock_fsopen:
                    with patch.object(chroma_agent.config, 'path', "/var/lib/chroma/", create=True):
                        self.assertEqual(agent_updates.configure_repo('filename', provided_content), agent_result_ok)
                        mock_fsopen.return_value.write.assert_called_once_with(expected_content)
                        mock_rename.assert_called_once_with('/etc/yum.repos.d/filename.tmp', '/etc/yum.repos.d/filename')

    def test_unconfigure_repo(self):
        self.assertEqual(agent_updates.unconfigure_repo(self.tmpRepo.name), agent_result_ok)
        self.assertFalse(os.path.exists(self.tmpRepo.name))

    def test_unconfigure_repo_no_file(self):
        os.remove(self.tmpRepo.name)
        self.assertFalse(os.path.exists(self.tmpRepo.name))
        self.assertEqual(agent_updates.unconfigure_repo(self.tmpRepo.name), agent_result_ok)

    def test_kernel_status(self):
        def try_run(args):
            if args == ["rpm", "-q", "kernel"]:
                return """kernel-2.6.32-358.2.1.el6.x86_64
kernel-2.6.32-358.18.1.el6_lustre.x86_64
"""

        with patch('chroma_agent.lib.shell.AgentShell.try_run', side_effect=try_run):
            result = agent_updates.kernel_status()
            self.assertDictEqual(result, {
                'required': 'kernel-2.6.32-358.18.1.el6_lustre.x86_64',
                'running': 'kernel-2.6.32-358.2.1.el6.x86_64',
                'available': [
                    "kernel-2.6.32-358.2.1.el6.x86_64",
                    "kernel-2.6.32-358.18.1.el6_lustre.x86_64"
                ]
            })

    def test_install_packages(self):
        self.add_commands(CommandCaptureCommand(('yum', 'clean', 'all', '--enablerepo=*')),
                          CommandCaptureCommand(('repoquery', '--requires', '--enablerepo=myrepo', 'foo', 'bar'),
                                                stdout="""/usr/bin/python
python >= 2.4
python(abi) = 2.6
yum >= 3.2.29
/bin/sh
kernel = 2.6.32-279.14.1.el6_lustre
lustre-backend-fs
        """),
                          CommandCaptureCommand(('yum', 'install', '-y', '--enablerepo=myrepo', 'foo', 'bar', 'kernel-2.6.32-279.14.1.el6_lustre')),
                          CommandCaptureCommand(('repoquery', '-q', '-a', '--qf=%{name} %{version}-%{release}.%{arch} %{repoid}',
                                                 '--pkgnarrow=updates', '--disablerepo=*', '--enablerepo=myrepo'), stdout="""
jasper-libs.x86_64                                                                             1.900.1-16.el6_6.3                                                                             myrepo
"""),
                          CommandCaptureCommand(('yum', 'update', '-y', '--enablerepo=myrepo', 'jasper-libs.x86_64')),
                          CommandCaptureCommand(('grubby', '--default-kernel'), stdout='/boot/vmlinuz-2.6.32-504.3.3.el6.x86_64'))

        def isfile(arg):
            return True

        with patch('os.path.isfile', side_effect=isfile):
            self.assertEqual(agent_updates.install_packages(['myrepo'], ['foo', 'bar']), agent_result({}))

        self.assertRanAllCommandsInOrder()

    def test_install_packages_hyd_4050_grubby(self):
        self.add_commands(CommandCaptureCommand(('yum', 'clean', 'all', '--enablerepo=*')),
                          CommandCaptureCommand(('repoquery', '--requires', '--enablerepo=myrepo', 'foo'), stdout="""/usr/bin/python
python >= 2.4
python(abi) = 2.6
yum >= 3.2.29
/bin/sh
kernel = 2.6.32-279.14.1.el6_lustre
lustre-backend-fs
        """),
                          CommandCaptureCommand(('yum', 'install', '-y', '--enablerepo=myrepo', 'foo', 'kernel-2.6.32-279.14.1.el6_lustre')),
                          CommandCaptureCommand(('repoquery', '-q', '-a', '--qf=%{name} %{version}-%{release}.%{arch} %{repoid}',
                                                 '--pkgnarrow=updates', '--disablerepo=*', '--enablerepo=myrepo')),
                          CommandCaptureCommand(('grubby', '--default-kernel'), rc=1))

        def isfile(arg):
            return True

        with patch('os.path.isfile', side_effect=isfile):
            self.assertTrue('error' in agent_updates.install_packages(['myrepo'], ['foo']))

        self.assertRanAllCommandsInOrder()

    def test_install_packages_4050_initramfs(self):
        self.add_commands(CommandCaptureCommand(('yum', 'clean', 'all', '--enablerepo=*')),
                          CommandCaptureCommand(('repoquery', '--requires', '--enablerepo=myrepo', 'foo'), stdout="""/usr/bin/python
python >= 2.4
python(abi) = 2.6
yum >= 3.2.29
/bin/sh
kernel = 2.6.32-279.14.1.el6_lustre
lustre-backend-fs
        """),
                          CommandCaptureCommand(('yum', 'install', '-y', '--enablerepo=myrepo', 'foo', 'kernel-2.6.32-279.14.1.el6_lustre')),
                          CommandCaptureCommand(('repoquery', '-q', '-a', '--qf=%{name} %{version}-%{release}.%{arch} %{repoid}',
                                                 '--pkgnarrow=updates', '--disablerepo=*', '--enablerepo=myrepo')),
                          CommandCaptureCommand(('grubby', '--default-kernel'), stdout='/boot/vmlinuz-2.6.32-504.3.3.el6.x86_64'))

        def isfile(arg):
            return False

        with patch('os.path.isfile', side_effect=isfile):
            self.assertTrue('error' in agent_updates.install_packages(['myrepo'], ['foo']))

        self.assertRanAllCommandsInOrder()

    def test_set_profile_success(self):
        config.update('settings', 'profile', {'managed': False})

        # Go from managed = False to managed = True
        self.add_command(('yum', 'install', '-y', '--enablerepo=iml-agent', 'chroma-agent-management'))
        self.assertEqual(agent_updates.update_profile({'managed': True}), agent_result_ok)
        self.assertRanAllCommandsInOrder()

        # Go from managed = True to managed = False
        self.reset_command_capture()
        self.add_command(('yum', 'remove', '-y', '--enablerepo=iml-agent', 'chroma-agent-management'))
        self.assertEqual(agent_updates.update_profile({'managed': False}), agent_result_ok)
        self.assertRanAllCommandsInOrder()

        # Go from managed = False to managed = False
        self.reset_command_capture()
        self.assertEqual(agent_updates.update_profile({'managed': False}), agent_result_ok)
        self.assertRanAllCommandsInOrder()

    def test_set_profile_fail(self):
        # Three times because yum will try three times.
        self.add_commands(CommandCaptureCommand(('yum', 'install', '-y', '--enablerepo=iml-agent', 'chroma-agent-management'), rc=1, stdout="Bad command stdout", stderr="Bad command stderr"),
                          CommandCaptureCommand(('yum', 'install', '-y', '--enablerepo=iml-agent', 'chroma-agent-management'), rc=1, stdout="Bad command stdout", stderr="Bad command stderr"),
                          CommandCaptureCommand(('yum', 'install', '-y', '--enablerepo=iml-agent', 'chroma-agent-management'), rc=1, stdout="Bad command stdout", stderr="Bad command stderr"))

        config.update('settings', 'profile', {'managed': False})

        # Go from managed = False to managed = True, but it will fail.
        self.assertEqual(agent_updates.update_profile({'managed': True}), agent_error('Unable to set profile because yum returned Bad command stdout'))
        self.assertRanAllCommandsInOrder()
