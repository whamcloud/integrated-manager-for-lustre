import os
import mock

import chroma_agent.device_plugins.audit
from chroma_agent.device_plugins.audit.local import LocalAudit
from chroma_agent.device_plugins.audit.node import NodeAudit
from chroma_agent.device_plugins.audit.lustre import LnetAudit, MdtAudit, MgsAudit

from tests.test_utils import PatchedContextTestCase
from chroma_common.test.command_capture_testcase import CommandCaptureTestCase


class TestAuditScanner(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        super(TestAuditScanner, self).setUp()

    def test_audit_scanner(self):
        """chroma_agent.device_plugins.audit.local_audit_classes() should return a list of classes."""
        list = [cls for cls in
                chroma_agent.device_plugins.audit.local_audit_classes()]
        self.assertEqual(list, [LnetAudit, MdtAudit, MgsAudit, NodeAudit])


class TestLocalAudit(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        super(TestLocalAudit, self).setUp()
        self.audit = LocalAudit()

    def test_localaudit_audit_classes(self):
        """LocalAudit.audit_classes() should return a list of classes."""
        self.assertEqual(self.audit.audit_classes(), [LnetAudit, MdtAudit, MgsAudit, NodeAudit])


class TestLocalAuditProperties(CommandCaptureTestCase):
    def setUp(self):
        super(TestLocalAuditProperties, self).setUp()
        self.node_audit = NodeAudit()

        mock.patch('platform.linux_distribution', return_value = ('Smarty', '2.2')).start()
        mock.patch('platform.python_version_tuple', return_value = (1, 2, 3)).start()
        mock.patch('platform.release', return_value = 'Bazinga').start()

        self.addCleanup(mock.patch.stopall)

    def test_zfs_property_installed(self):
        self.add_command(('which', 'zfs'), stdout="/sbin/zfs")
        self.assertEqual(self.node_audit.properties()['zfs_installed'], True)

    def test_zfs_property_not_installed(self):
        self.add_command(('which', 'zfs'), rc=1, stderr="which: no zfs in (/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin)")
        self.assertEqual(self.node_audit.properties()['zfs_installed'], False)

    def test_platform_values(self):
        self.add_command(('which', 'zfs'), rc=1, stderr="which: no zfs in (/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin)")

        properties = self.node_audit.properties()

        self.assertEqual(properties['distro'], 'Smarty')
        self.assertEqual(properties['distro_version'], 2.2)
        self.assertEqual(properties['python_version_major_minor'], 1.2)
        self.assertEqual(properties['python_patchlevel'], 3)
        self.assertEqual(properties['kernel_version'], 'Bazinga')
