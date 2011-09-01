import unittest
import tempfile
import os, shutil
from hydra_agent.audit import BaseAudit
from hydra_agent.audit.mixins import FileSystemMixin

class TestFileSystemMixinWithDefaultContext(unittest.TestCase):
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_root, "etc"))
        f = open(os.path.join(self.test_root, "etc/passwd"), "w+")
        f.write("root:*:0:0:System Administrator:/var/root:/bin/sh\n")
        f.close()

        class TestAudit(BaseAudit, FileSystemMixin):
            def __init__(self, fscontext=None, **kwargs):
                if fscontext is not None:
                    self.fscontext = fscontext

        self.audit = TestAudit()

    def test_default_context(self):
        """Test that the mixin works without a context supplied."""
        filter = lambda line: line.startswith("root")
        assert "root" in self.audit.read_lines("/etc/passwd", filter)[0]

class TestFileSystemMixinWithContextInConstructor(unittest.TestCase):
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_root, "etc"))
        f = open(os.path.join(self.test_root, "etc/passwd"), "w+")
        f.write("root:*:0:0:System Administrator:/var/root:/bin/sh\n")
        f.close()

        class TestAudit(BaseAudit, FileSystemMixin):
            def __init__(self, fscontext=None, **kwargs):
                if fscontext is not None:
                    self.fscontext = fscontext

        self.constructor = TestAudit(fscontext=self.test_root)
        self.set_later = TestAudit()

    def test_fscontext_in_constructor(self):
        """Test that the mixin works with fscontext supplied in constructor."""
        filter = lambda line: line.startswith("root")
        assert "root" in self.constructor.read_lines("/etc/passwd", filter)[0]

    def test_fscontext_set_later(self):
        """Test that the mixin works with fscontext set after instantiation."""
        self.set_later.context = self.test_root
        filter = lambda line: line.startswith("root")
        assert "root" in self.set_later.read_lines("/etc/passwd", filter)[0]

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

        f = open(os.path.join(self.test_root, "proc/fs/lustre/int_file"), "w+")
        f.write("4242\n")
        f.close()

        class TestAudit(BaseAudit, FileSystemMixin):
            pass
        self.audit = TestAudit()
        self.audit.fscontext = self.test_root

    def test_readlines(self):
        """Test that readlines() returns a list of strings."""
        lines = self.audit.read_lines("/proc/fs/lustre/version")
        assert lines[0] == "lustre: 1.8.3"

    def test_readlines_filter(self):
        """Test that readlines() accepts and uses a line filter function."""
        filter = lambda line: "build:" in line
        lines = self.audit.read_lines("/proc/fs/lustre/version", filter)
        assert lines[0] == "build:  1.8.3-20100409182943-PRISTINE-2.6.18-164.11.1.el5_lustre.1.8.3"

    def test_readstring(self):
        """Test that read_string() returns a single string."""
        string = self.audit.read_string("/proc/fs/lustre/version")
        assert string == "lustre: 1.8.3"

    def test_readint(self):
        """Test that read_int() returns a single int."""
        test_int = self.audit.read_int("/proc/fs/lustre/int_file")
        assert test_int == 4242

    def tearDown(self):
        shutil.rmtree(self.test_root)
