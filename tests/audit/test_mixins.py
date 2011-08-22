import unittest
import tempfile
import os, shutil
from hydra_agent.audit import BaseAudit
from hydra_agent.audit.mixins import FileSystemMixin

class TestFileSystemMixin:
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_root, "proc/fs/lustre"))
        f = open(os.path.join(self.test_root, "proc/fs/lustre/version"), "w+")
        f.write("""lustre: 1.8.3
kernel: patchless_client
build:  1.8.3-20100409182943-PRISTINE-2.6.18-164.11.1.el5_lustre.1.8.3
        """)
        f.close()

        class TestAudit(BaseAudit, FileSystemMixin):
            pass
        self.audit = TestAudit()
        self.audit.context = self.test_root


    def test_readlines(self):
        lines = self.audit.read_lines("/proc/fs/lustre/version")
        assert lines[0] == "lustre: 1.8.3"

    def test_readlines_filter(self):
        filter = lambda line: "build:" in line
        lines = self.audit.read_lines("/proc/fs/lustre/version", filter)
        assert lines[0] == "build:  1.8.3-20100409182943-PRISTINE-2.6.18-164.11.1.el5_lustre.1.8.3"

    def test_readstring(self):
        string = self.audit.read_string("/proc/fs/lustre/version")
        assert string == "lustre: 1.8.3"

    def tearDown(self):
        shutil.rmtree(self.test_root)
