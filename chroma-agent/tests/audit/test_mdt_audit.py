import os
from chroma_agent.device_plugins.audit.lustre import MdtAudit

from tests.test_utils import PatchedContextTestCase


class TestMdtAudit(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.9.58_86_g2383a62/mds_mgs")
        super(TestMdtAudit, self).setUp()
        self.audit = MdtAudit()

    def test_audit_is_available(self):
        assert MdtAudit.is_available()
