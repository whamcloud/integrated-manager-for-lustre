import mock
import os
from tempfile import NamedTemporaryFile

from mock import patch
from django.utils.unittest.case import TestCase

from chroma_agent.action_plugins import agent_updates
from chroma_agent.device_plugins import lustre
from chroma_agent import config
from chroma_agent.chroma_common.lib.shell import CommandExecutionError


class TestManageUpdates(TestCase):
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
[Intel Lustre Manager]
name=Intel Lustre Manager updates
baseurl=http://www.test.com/test.repo
enabled=1
gpgcheck=0
sslverify = 1
sslcacert = /var/lib/chroma/authority.crt
sslclientkey = /var/lib/chroma/private.pem
sslclientcert = /var/lib/chroma/self.crt
"""
        with patch('__builtin__.open', spec=file, create=True) as mock_open:
            with patch.object(chroma_agent.config, 'path', "/var/lib/chroma/", create=True):
                agent_updates.configure_repo('http://www.test.com/test.repo')
                mock_open.return_value.write.assert_called_once_with(expected_content)

    def test_unconfigure_repo(self):
        agent_updates.unconfigure_repo(self.tmpRepo.name)
        self.assertFalse(os.path.exists(self.tmpRepo.name))

    def test_update_packages(self):
        def try_run(args):
            if args == ['repoquery', '--disablerepo=*', "--enablerepo=myrepo", "--pkgnarrow=updates", "-a"]:
                return """chroma-agent-99.01-3061.noarch
chroma-agent-management-99.01-3061.noarch
"""
            else:
                return ""

        with patch('chroma_agent.chroma_common.lib.shell.try_run', side_effect=try_run) as mock_try_run:
            agent_updates.update_packages(['myrepo'], ['mypackage'])
            self.assertListEqual(list(mock_try_run.call_args_list[0][0][0]), ['yum', 'clean', 'all'])
            self.assertListEqual(list(mock_try_run.call_args_list[1][0][0]), ['repoquery', '--disablerepo=*', "--enablerepo=myrepo", "--pkgnarrow=updates", "-a"])
            self.assertListEqual(list(mock_try_run.call_args_list[2][0][0]), ['repoquery', '--requires', 'mypackage'])
            self.assertListEqual(list(mock_try_run.call_args_list[3][0][0]), ['yum', 'update', '-y', "--enablerepo=myrepo", "chroma-agent-99.01-3061.noarch", "chroma-agent-management-99.01-3061.noarch"])

    def test_install_packages(self):
        with patch('chroma_agent.chroma_common.lib.shell.try_run') as mock_run:
            agent_updates.install_packages(['myrepo'], ['foo', 'bar'])
            mock_run.assert_called_once_with(['yum', 'install', '-y', "--enablerepo=myrepo", 'foo', 'bar'])

    def test_kernel_status(self):
        def try_run(args):
            if args == ["rpm", "-qR", "lustre-modules"]:
                return """/bin/sh
/bin/sh
/bin/sh
kernel = 2.6.32-358.18.1.el6
rpmlib(CompressedFileNames) <= 3.0.4-1
rpmlib(FileDigests) <= 4.6.0-1
rpmlib(PayloadFilesHavePrefix) <= 4.0-1
rpmlib(PayloadIsXz) <= 5.2-1
"""
            elif args == ["uname", "-r"]:
                return "2.6.32-358.2.1.el6.x86_64\n"
            elif args == ["rpm", "-q", "kernel"]:
                return """kernel-2.6.32-358.2.1.el6.x86_64
kernel-2.6.32-358.18.1.el6.x86_64
"""

        with patch('chroma_agent.chroma_common.lib.shell.try_run', side_effect=try_run):
            result = agent_updates.kernel_status()
            self.assertDictEqual(result, {
                'required': 'kernel-2.6.32-358.18.1.el6.x86_64',
                'running': 'kernel-2.6.32-358.2.1.el6.x86_64',
                'available': [
                    "kernel-2.6.32-358.2.1.el6.x86_64",
                    "kernel-2.6.32-358.18.1.el6.x86_64"
                ]
            })

    def test_install_packages_force(self):
        def try_run(args):
            if args == ['repoquery', '--requires', "--enablerepo=myrepo", 'foo']:
                return """/usr/bin/python
python >= 2.4
python(abi) = 2.6
yum >= 3.2.29
/bin/sh
kernel = 2.6.32-279.14.1.el6_lustre
lustre-backend-fs

"""

        with patch('chroma_agent.chroma_common.lib.shell.try_run', side_effect=try_run) as mock_run:
            agent_updates.install_packages(['myrepo'], ['foo'], force_dependencies=True)
            self.assertListEqual(
                mock_run.call_args_list,
                [
                    mock.call(['repoquery', '--requires', '--enablerepo=myrepo', 'foo']),
                    mock.call(['yum', 'install', '-y', '--enablerepo=myrepo', 'kernel-2.6.32-279.14.1.el6_lustre']),
                    mock.call(['yum', 'install', '-y', '--enablerepo=myrepo', 'foo'])
                ]
            )

    def test_set_profile_success(self):
        self.mock_read_uri_result = None

        def mock_try_run(args):
            if args == ['yum', 'install', '-y', '--enablerepo=iml-agent', 'chroma-agent-management']:
                return ""
            if args == ['yum', 'remove', '-y', '--enablerepo=iml-agent', 'chroma-agent-management']:
                return ""
            else:
                raise CommandExecutionError(1, args, "Bad command stdout", "Bad command stderr")

        def mock_ReadServerURI(args):
            return self.mock_read_uri_result

        with patch('chroma_agent.chroma_common.lib.shell.try_run', side_effect=mock_try_run) as mtr:
            with patch('chroma_agent.utils.ReadServerURI', side_effect=mock_ReadServerURI):
                config.update('settings', 'profile', {'managed': False})

                # Go from managed = False to managed = True
                self.mock_read_uri_result = {'objects': [{'managed': True}]}
                self.assertEqual(agent_updates.set_profile('test_profile'), None)
                self.assertListEqual(list(mtr.call_args_list[0][0][0]), ['yum', 'install', '-y', '--enablerepo=iml-agent', 'chroma-agent-management'])

                # Go from managed = True to managed = False
                mtr.reset_mock()
                self.mock_read_uri_result = {'objects': [{'managed': False}]}
                self.assertEqual(agent_updates.set_profile('test_profile'), None)
                self.assertListEqual(list(mtr.call_args_list[0][0][0]), ['yum', 'remove', '-y', '--enablerepo=iml-agent', 'chroma-agent-management'])

                # Go from managed = False to managed = False
                mtr.reset_mock()
                self.assertEqual(agent_updates.set_profile('test_profile'), None)
                self.assertEqual(mtr.call_count, 0)

    def test_set_profile_fail(self):
        self.mock_read_uri_result = None

        def mock_try_run(args):
            raise CommandExecutionError(1, args, "Bad command stdout", "Bad command stderr")

        def mock_ReadServerURI(args):
            return self.mock_read_uri_result

        with patch('chroma_agent.chroma_common.lib.shell.try_run', side_effect=mock_try_run) as mtr:
            with patch('chroma_agent.utils.ReadServerURI', side_effect=mock_ReadServerURI):
                config.update('settings', 'profile', {'managed': False})

                # Go from managed = False to managed = True, but it will fail.
                self.mock_read_uri_result = {'objects': [{'managed': True}]}
                self.assertEqual(agent_updates.set_profile('test_profile'), 'Unable to set profile because yum returned Bad command stdout')
                self.assertEqual(mtr.call_count, 3)     # 3 because it will try the yum command 3 times.
