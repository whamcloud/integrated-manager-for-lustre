import os
from chroma_agent.device_plugins.audit.lustre import LnetAudit

from tests.test_utils import PatchedContextTestCase


class TestLnetAudit(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        super(TestLnetAudit, self).setUp()
        self.audit = LnetAudit()

    def test_audit_is_available(self):
        assert LnetAudit.is_available()
