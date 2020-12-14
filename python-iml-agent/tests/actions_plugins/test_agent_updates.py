import mock
import os
from tempfile import NamedTemporaryFile

from mock import patch

from chroma_agent.action_plugins import agent_updates
from chroma_agent import config
from iml_common.lib.shell import Shell
from iml_common.test.command_capture_testcase import (
    CommandCaptureTestCase,
    CommandCaptureCommand,
)
from iml_common.lib.agent_rpc import agent_result, agent_result_ok, agent_error


class TestManageUpdates(CommandCaptureTestCase):
    def setUp(self):
        super(TestManageUpdates, self).setUp()
        self.tmpRepo = NamedTemporaryFile(delete=False)

    def tearDown(self):
        if os.path.exists(self.tmpRepo.name):
            os.remove(self.tmpRepo.name)

    def test_configure_repo(self):
        import chroma_agent

        expected_content = """
[Integrated-Manager-For-Lustre]
name=Integrated Manager for Lustre updates
baseurl=http://www.test.com/test.repo
enabled=1
gpgcheck=0
sslverify = 1
sslcacert = /etc/iml/authority.crt
sslclientkey = /etc/iml/private.pem
sslclientcert = /etc/iml/self.crt
"""
        provided_content = """
[Integrated-Manager-For-Lustre]
name=Integrated Manager for Lustre updates
baseurl=http://www.test.com/test.repo
enabled=1
gpgcheck=0
sslverify = 1
sslcacert = {0}
sslclientkey = {1}
sslclientcert = {2}
"""
        with patch("os.rename", create=True) as mock_rename:
            with patch("os.open", create=True):
                with patch("os.fdopen", spec=file, create=True) as mock_fsopen:
                    with patch.object(chroma_agent.config, "path", "/var/lib/chroma/", create=True):
                        self.assertEqual(
                            agent_updates.configure_repo("filename", provided_content),
                            agent_result_ok,
                        )
                        mock_fsopen.return_value.write.assert_called_once_with(expected_content)
                        mock_rename.assert_called_once_with(
                            "/etc/yum.repos.d/filename.tmp", "/etc/yum.repos.d/filename"
                        )

    def test_unconfigure_repo(self):
        self.assertEqual(agent_updates.unconfigure_repo(self.tmpRepo.name), agent_result_ok)
        self.assertFalse(os.path.exists(self.tmpRepo.name))

    def test_unconfigure_repo_no_file(self):
        os.remove(self.tmpRepo.name)
        self.assertFalse(os.path.exists(self.tmpRepo.name))
        self.assertEqual(agent_updates.unconfigure_repo(self.tmpRepo.name), agent_result_ok)

    def test_kernel_status(self):
        def run(arg_list):
            values = {
                ("rpm", "-q", "kernel"): {
                    "rc": 0,
                    "stdout": "kernel-2.6.32-358.2.1.el6.x86_64\n" "kernel-2.6.32-358.18.1.el6_lustre.x86_64\n",
                },
                ("rpm", "-q", "--whatprovides", "kmod-lustre"): {
                    "rc": 0,
                    "stdout": "kmod-lustre-1.2.3-1.el6.x86_64\n",
                },
                ("rpm", "-ql", "--whatprovides", "lustre-osd", "kmod-lustre"): {
                    "rc": 0,
                    "stdout": "/lib/modules/2.6.32-358.18.1.el7_lustre.x86_64/extra/lustre/fs/lustre.ko\n"
                    "/lib/modules/2.6.32-358.18.1.el7_lustre.x86_64/extra/lustre-osd-ldiskfs/fs/osd_ldiskfs.ko\n",
                },
                (
                    "modinfo",
                    "-n",
                    "-k",
                    "2.6.32-358.2.1.el6.x86_64",
                    "lustre",
                    "osd_ldiskfs",
                ): {"rc": 1, "stdout": ""},
                ("modinfo", "-n", "-k", "2.6.32-358.18.1.el6_lustre.x86_64", "lustre", "osd_ldiskfs",): {
                    "rc": 0,
                    "stdout": "/lib/modules/2.6.32-358.18.1.el7_lustre.x86_64/extra/lustre/fs/lustre.ko\n"
                    "/lib/modules/2.6.32-358.18.1.el7_lustre.x86_64/extra/lustre-osd-ldiskfs/fs/osd_ldiskfs.ko\n",
                },
                ("uname", "-m"): {"rc": 0, "stdout": "x86_64\n"},
                ("uname", "-r"): {"rc": 0, "stdout": "2.6.32-358.2.1.el6.x86_64\n"},
            }
            return Shell.RunResult(
                values[tuple(arg_list)]["rc"],
                values[tuple(arg_list)]["stdout"],
                "",
                False,
            )

        with patch("chroma_agent.lib.shell.AgentShell.run", side_effect=run):
            result = agent_updates.kernel_status()
            self.assertDictEqual(
                result,
                {
                    "required": "kernel-2.6.32-358.18.1.el6_lustre.x86_64",
                    "running": "kernel-2.6.32-358.2.1.el6.x86_64",
                    "available": [
                        "kernel-2.6.32-358.2.1.el6.x86_64",
                        "kernel-2.6.32-358.18.1.el6_lustre.x86_64",
                    ],
                },
            )

    def test_selinux_status(self):
        def run(arg_list):
            values = {("getenforce",): "Enforcing\n"}
            return Shell.RunResult(0, values[tuple(arg_list)], "", False)

        with patch("chroma_agent.lib.shell.AgentShell.run", side_effect=run):
            result = agent_updates.selinux_status()
            self.assertDictEqual(result, {"status": "Enforcing"})

    def test_selinux_status_missing(self):
        def run(arg_list):
            values = {("getenforce",): ""}
            return Shell.RunResult(127, values[tuple(arg_list)], "getenforce: command not found", False)

        with patch("chroma_agent.lib.shell.AgentShell.run", side_effect=run):
            result = agent_updates.selinux_status()
            self.assertDictEqual(result, {"status": "Disabled"})

    def test_install_packages(self):
        self.add_commands(
            CommandCaptureCommand(("yum", "clean", "all", "--enablerepo=*")),
            CommandCaptureCommand(
                ("repoquery", "--requires", "--enablerepo=myrepo", "foo", "bar"),
                stdout="""/usr/bin/python
python >= 2.4
python(abi) = 2.6
yum >= 3.2.29
/bin/sh
kernel = 2.6.32-279.14.1.el6_lustre
lustre-backend-fs
        """,
            ),
            CommandCaptureCommand(
                (
                    "yum",
                    "install",
                    "-y",
                    "--exclude",
                    "kernel-debug",
                    "--enablerepo=myrepo",
                    "foo",
                    "bar",
                    "kernel-2.6.32-279.14.1.el6_lustre",
                )
            ),
            CommandCaptureCommand(
                ("grubby", "--default-kernel"),
                stdout="/boot/vmlinuz-2.6.32-504.3.3.el6.x86_64",
            ),
            CommandCaptureCommand(("systemctl", "start", "iml-update-check")),
            CommandCaptureCommand(("systemctl", "is-active", "iml-update-check")),
        )

        def isfile(arg):
            return True

        with patch("os.path.isfile", side_effect=isfile):
            self.assertEqual(
                agent_updates.install_packages(["myrepo"], ["foo", "bar"]),
                agent_result_ok,
            )

        self.assertRanAllCommandsInOrder()

    def test_install_packages_hyd_4050_grubby(self):
        self.add_commands(
            CommandCaptureCommand(("yum", "clean", "all", "--enablerepo=*")),
            CommandCaptureCommand(
                ("repoquery", "--requires", "--enablerepo=myrepo", "foo"),
                stdout="""/usr/bin/python
python >= 2.4
python(abi) = 2.6
yum >= 3.2.29
/bin/sh
kernel = 2.6.32-279.14.1.el6_lustre
lustre-backend-fs
        """,
            ),
            CommandCaptureCommand(
                (
                    "yum",
                    "install",
                    "-y",
                    "--exclude",
                    "kernel-debug",
                    "--enablerepo=myrepo",
                    "foo",
                    "kernel-2.6.32-279.14.1.el6_lustre",
                )
            ),
            CommandCaptureCommand(("grubby", "--default-kernel"), rc=1),
        )

        def isfile(arg):
            return True

        with patch("os.path.isfile", side_effect=isfile):
            self.assertTrue("error" in agent_updates.install_packages(["myrepo"], ["foo"]))

        self.assertRanAllCommandsInOrder()

    def test_install_packages_4050_initramfs(self):
        self.add_commands(
            CommandCaptureCommand(("yum", "clean", "all", "--enablerepo=*")),
            CommandCaptureCommand(
                ("repoquery", "--requires", "--enablerepo=myrepo", "foo"),
                stdout="""/usr/bin/python
python >= 2.4
python(abi) = 2.6
yum >= 3.2.29
/bin/sh
kernel = 2.6.32-279.14.1.el6_lustre
lustre-backend-fs
        """,
            ),
            CommandCaptureCommand(
                (
                    "yum",
                    "install",
                    "-y",
                    "--exclude",
                    "kernel-debug",
                    "--enablerepo=myrepo",
                    "foo",
                    "kernel-2.6.32-279.14.1.el6_lustre",
                )
            ),
            CommandCaptureCommand(
                ("grubby", "--default-kernel"),
                stdout="/boot/vmlinuz-2.6.32-504.3.3.el6.x86_64",
            ),
        )

        def isfile(arg):
            return False

        with patch("os.path.isfile", side_effect=isfile):
            self.assertTrue("error" in agent_updates.install_packages(["myrepo"], ["foo"]))

        self.assertRanAllCommandsInOrder()
