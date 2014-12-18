import tempfile
import os
from chroma_agent.device_plugins.audit.lustre import ClientAudit

from tests.test_utils import PatchedContextTestCase


class TestClientAudit(PatchedContextTestCase):
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        super(TestClientAudit, self).setUp()
        os.makedirs(os.path.join(self.test_root, "proc"))
        with open(os.path.join(self.test_root, "proc/mounts"), "w+") as f:
            f.write("10.0.0.129@tcp:/testfs /mnt/lustre_clients/testfs lustre rw 0 0\n")
        self.audit = ClientAudit()

    def test_audit_is_available(self):
        assert ClientAudit.is_available()

    def test_gathered_mount_list(self):
        actual_list = self.audit.metrics()['raw']['lustre_client_mounts']
        expected_list = [dict(mountspec = '10.0.0.129@tcp:/testfs',
                              mountpoint = '/mnt/lustre_clients/testfs')]
        self.assertEqual(actual_list, expected_list)
