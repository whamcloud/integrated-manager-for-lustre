import mock
import os
from glob import glob
import unittest
from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import daemon_log


class PatchedContextTestCase(unittest.TestCase):
    def __init__(self, methodName):
        super(PatchedContextTestCase, self).__init__(methodName)
        self._test_root = None
        self._orig_root = None

        def mock_scanner_cmd(cmd):
            if cmd == "GetMounts":
                return []
            else:
                return [{}, {}]

        mock.patch("chroma_agent.device_plugins.block_devices.scanner_cmd", mock_scanner_cmd).start()

    def setUp(self):
        mock.patch(
            "chroma_agent.device_plugins.audit.mixins.LustreGetParamMixin.get_param_lines",
            self.mock_get_param_lines,
        ).start()
        mock.patch(
            "chroma_agent.device_plugins.audit.mixins.LustreGetParamMixin.get_param_raw",
            self.mock_get_param_raw,
        ).start()
        mock.patch(
            "chroma_agent.device_plugins.audit.mixins.LustreGetParamMixin.list_params",
            self.mock_list_params,
        ).start()
        self.addCleanup(mock.patch.stopall)
        super(PatchedContextTestCase, self).setUp()

    def _find_subclasses(self, klass):
        """Introspectively find all descendents of a class"""
        subclasses = []
        for subclass in klass.__subclasses__():
            subclasses.append(subclass)
            subclasses.extend(self._find_subclasses(subclass))
        return subclasses

    def mock_get_param_lines(self, path, filter_f=None):
        param = path.replace("/", ".")
        daemon_log.info("mock_get_params_lines: " + param)
        flist = glob(param)
        if not flist:
            raise AgentShell.CommandExecutionError(
                AgentShell.RunResult(
                    2,
                    "",
                    "error: get_param: param_path '" + param + "': No such file or directory",
                    0,
                ),
                ["lctl", "get_param", "-n", path],
            )
        for fn in flist:
            with open(fn, "r") as content_file:
                for line in content_file:
                    if filter_f:
                        if filter_f(line):
                            yield line.strip()
                    else:
                        yield line.strip()

    def mock_get_param_raw(self, path):
        param = path.replace("/", ".")
        daemon_log.info("mock_get_params_lines: " + param)
        data = ""
        for fn in glob(param):
            with open(fn, "r") as content_file:
                data += content_file.read()
        if data:
            return data
        else:
            raise AgentShell.CommandExecutionError(
                AgentShell.RunResult(
                    2,
                    "",
                    "error: get_param: param_path '" + param + "': No such file or directory",
                    0,
                ),
                ["lctl", "get_param", "-n", path],
            )

    def mock_list_params(self, path):
        fl = glob(path)
        if fl:
            daemon_log.info("mock_list_params: " + path)
            return fl
        else:
            raise AgentShell.CommandExecutionError(
                AgentShell.RunResult(
                    2,
                    "",
                    "error: get_param: param_path '" + path + "': No such file or directory",
                    0,
                ),
                ["lctl", "get_param", "-N", path],
            )

    @property
    def test_root(self):
        return self._test_root

    @test_root.setter
    def test_root(self, value):
        assert self._test_root is None, "test_root can only be set once per test"

        self._test_root = value
        self._orig_root = os.getcwd()
        os.chdir(self._test_root)

        from chroma_agent.device_plugins.audit import BaseAudit

        for subclass in self._find_subclasses(BaseAudit):
            mock.patch.object(subclass, "fscontext", self._test_root).start()

        self.addCleanup(mock.patch.stopall)
        self.addCleanup(os.chdir, self._orig_root)
