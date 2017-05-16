import os
from chroma_agent.device_plugins.audit.node import NodeAudit

from tests.test_utils import PatchedContextTestCase


class TestNodeMetrics(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.9.58_86_g2383a62/mds_mgs")
        super(TestNodeMetrics, self).setUp()
        self.audit = NodeAudit()
        self.metrics = self.audit.metrics()

    def test_node_cpustats(self):
        self.assertEqual(self.metrics['raw']['node']['cpustats']['total'], 10309070)
        self.assertEqual(self.metrics['raw']['node']['cpustats']['user'], 360581)

    def test_node_meminfo(self):
        self.assertEqual(self.metrics['raw']['node']['meminfo']['MemTotal'], 1883716)
