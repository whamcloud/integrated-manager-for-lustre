import os
from chroma_agent.device_plugins.audit.lustre import MdsAudit

from tests.test_utils import PatchedContextTestCase


class TestMdsAudit(PatchedContextTestCase):

    def test_mdd_obd_skipped(self):
        """Test that the mdd_obd device is skipped for 2.x audits (HYD-437)"""
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(
            tests, "data/lustre_versions/2.9.58_86_g2383a62/mds_mgs")
        super(TestMdsAudit, self).setUp()
        self.assertFalse(MdsAudit.is_available())
