from django.utils import unittest
import os
from hydra_agent.audit.node import NodeAudit


class TestNodeMetrics(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        self.audit = NodeAudit(fscontext=test_root)
        self.metrics = self.audit.metrics()

    def test_node_cpustats(self):
        self.assertEqual(self.metrics['raw']['node']['cpustats']['total'], 3540537)
        self.assertEqual(self.metrics['raw']['node']['cpustats']['user'], 24601)

    def test_node_meminfo(self):
        self.assertEqual(self.metrics['raw']['node']['meminfo']['MemTotal'], 3991680)
