import mock
import os
from tempfile import NamedTemporaryFile

from mock import patch
from django.utils.unittest.case import TestCase

from chroma_agent.action_plugins import manage_updates
from chroma_agent.device_plugins import lustre


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
            with patch('chroma_agent.store.AgentStore.libdir', return_value="/var/lib/chroma/"):
                manage_updates.configure_repo('http://www.test.com/test.repo')
                mock_open.return_value.write.assert_called_once_with(expected_content)

    def test_unconfigure_repo(self):
        manage_updates.unconfigure_repo(self.tmpRepo.name)
        self.assertFalse(os.path.exists(self.tmpRepo.name))

    def test_update_packages(self):
        def try_run(args):
            if args == ['repoquery', '--disablerepo=*', "--enablerepo=myrepo", "--pkgnarrow=updates", "-a"]:
                return """chroma-agent-99.01-3061.noarch
chroma-agent-management-99.01-3061.noarch
"""
            else:
                return ""

        with patch('chroma_agent.shell.try_run', side_effect=try_run) as mock_try_run:
            manage_updates.update_packages(['myrepo'], ['mypackage'])
            self.assertListEqual(list(mock_try_run.call_args_list[0][0][0]), ['yum', 'clean', 'all'])
            self.assertListEqual(list(mock_try_run.call_args_list[1][0][0]), ['repoquery', '--disablerepo=*', "--enablerepo=myrepo", "--pkgnarrow=updates", "-a"])
            self.assertListEqual(list(mock_try_run.call_args_list[2][0][0]), ['repoquery', '--requires', 'mypackage'])
            self.assertListEqual(list(mock_try_run.call_args_list[3][0][0]), ['yum', '-y', 'update', "chroma-agent-99.01-3061.noarch", "chroma-agent-management-99.01-3061.noarch"])

    def test_install_packages(self):
        with patch('chroma_agent.shell.try_run') as mock_run:
            manage_updates.install_packages(['foo', 'bar'])
            mock_run.assert_called_once_with(['yum', 'install', '-y', 'foo', 'bar'])

    def test_kernel_status(self):
        def try_run(args):
            if args == ["rpm", "-q", "kernel", "--qf", "%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH} %{INSTALLTIME}\\n"]:
                return """kernel-2.6.32-358.el6.x86_64 1363856095
kernel-2.6.32-358.2.1.el6.x86_64 1363856467
kernel-2.6.32-279.14.1.el6_lustre.x86_64 1366712894
"""
            elif args == ["uname", "-r"]:
                return "2.6.32-358.2.1.el6.x86_64\n"

        with patch('chroma_agent.shell.try_run', side_effect=try_run):
            result = manage_updates.kernel_status(".*lustre.*")
            self.assertDictEqual(result, {
                'latest': 'kernel-2.6.32-279.14.1.el6_lustre.x86_64',
                'running': 'kernel-2.6.32-358.2.1.el6.x86_64'
            })

    def test_install_packages_force(self):
        def try_run(args):
            if args == ['repoquery', '--requires', 'foo']:
                return """/usr/bin/python
python >= 2.4
python(abi) = 2.6
yum >= 3.2.29
/bin/sh
kernel = 2.6.32-279.14.1.el6_lustre
lustre-backend-fs

"""

        with patch('chroma_agent.shell.try_run', side_effect=try_run) as mock_run:
            manage_updates.install_packages(['foo'], force_dependencies=True)
            self.assertListEqual(
                mock_run.call_args_list,
                [
                    mock.call(['repoquery', '--requires', 'foo']),
                    mock.call(['yum', 'install', '-y', 'kernel-2.6.32-279.14.1.el6_lustre']),
                    mock.call(['yum', 'install', '-y', 'foo'])
                ]
            )
