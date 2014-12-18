import os
from chroma_agent.device_plugins.audit.lustre import ObdfilterAudit

from tests.test_utils import PatchedContextTestCase


class TestObdfilterAudit(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/oss")
        super(TestObdfilterAudit, self).setUp()
        self.audit = ObdfilterAudit()

    def test_audit_is_available(self):
        assert ObdfilterAudit.is_available()
