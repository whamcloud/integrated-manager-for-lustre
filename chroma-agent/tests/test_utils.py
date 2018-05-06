import StringIO

from django.utils import unittest
from chroma_agent.utils import Mounts
import mock


def patch_open(path_to_result):
    """Return a context manager intercepting calls to 'open' so as to return
    a static result string on read()s according to the path"""

    def fake_open(path, *args):
        return StringIO.StringIO(path_to_result[path])

    return mock.patch('__builtin__.open', fake_open, create=True)


class TestMounts(unittest.TestCase):
    def test_load(self):
        path_to_result = {
            '/proc/mounts':
            """rootfs / rootfs rw 0 0
            proc /proc proc rw,relatime 0 0
            sysfs /sys sysfs rw,relatime 0 0
            devtmpfs /dev devtmpfs rw,relatime,size=475232k,nr_inodes=118808,mode=755 0 0
            devpts /dev/pts devpts rw,relatime,gid=5,mode=620,ptmxmode=000 0 0
            tmpfs /dev/shm tmpfs rw,relatime 0 0
            /dev/mapper/LustreVG-root / ext3 rw,relatime,errors=continue,user_xattr,acl,barrier=1,data=ordered 0 0
            /proc/bus/usb /proc/bus/usb usbfs rw,relatime 0 0
            /dev/sda1 /boot ext3 rw,relatime,errors=continue,user_xattr,acl,barrier=1,data=ordered 0 0
            /dev/mapper/LustreVG-usr /usr ext3 rw,relatime,errors=continue,user_xattr,acl,barrier=1,data=ordered 0 0
            /dev/mapper/LustreVG-var /var ext3 rw,relatime,errors=continue,user_xattr,acl,barrier=1,data=ordered 0 0
            none /proc/sys/fs/binfmt_misc binfmt_misc rw,relatime 0 0
            sunrpc /var/lib/nfs/rpc_pipefs rpc_pipefs rw,relatime 0 0"""
        }

        expected_result = [('rootfs', '/',
                            'rootfs'), ('proc', '/proc',
                                        'proc'), ('sysfs', '/sys', 'sysfs'),
                           ('devtmpfs', '/dev',
                            'devtmpfs'), ('devpts', '/dev/pts',
                                          'devpts'), ('tmpfs', '/dev/shm',
                                                      'tmpfs'),
                           ('/dev/mapper/LustreVG-root', '/',
                            'ext3'), ('/proc/bus/usb', '/proc/bus/usb',
                                      'usbfs'), ('/dev/sda1', '/boot', 'ext3'),
                           ('/dev/mapper/LustreVG-usr', '/usr',
                            'ext3'), ('/dev/mapper/LustreVG-var', '/var',
                                      'ext3'), ('none',
                                                '/proc/sys/fs/binfmt_misc',
                                                'binfmt_misc'),
                           ('sunrpc', '/var/lib/nfs/rpc_pipefs', 'rpc_pipefs')]

        with patch_open(path_to_result):
            result = Mounts().all()
            self.assertListEqual(result, expected_result)


class PatchedContextTestCase(unittest.TestCase):
    def __init__(self, methodName):
        super(PatchedContextTestCase, self).__init__(methodName)
        self._test_root = None

    def _find_subclasses(self, klass):
        """Introspectively find all descendents of a class"""
        subclasses = []
        for subclass in klass.__subclasses__():
            subclasses.append(subclass)
            subclasses.extend(self._find_subclasses(subclass))
        return subclasses

    @property
    def test_root(self):
        return self._test_root

    @test_root.setter
    def test_root(self, value):
        assert self._test_root == None, "test_root can only be set once per test"

        self._test_root = value

        from chroma_agent.device_plugins.audit import BaseAudit
        for subclass in self._find_subclasses(BaseAudit):
            mock.patch.object(subclass, 'fscontext', self._test_root).start()

        # These classes aren't reliably detected for patching.
        from chroma_agent.device_plugins.audit.node import NodeAudit
        mock.patch.object(NodeAudit, 'fscontext', self._test_root).start()
        from chroma_agent.utils import Mounts
        mock.patch.object(Mounts, 'fscontext', self._test_root).start()

        self.addCleanup(mock.patch.stopall)
