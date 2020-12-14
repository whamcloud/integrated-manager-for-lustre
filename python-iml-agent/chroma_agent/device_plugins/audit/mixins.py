# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
from chroma_agent.lib.shell import AgentShell


class LustreGetParamMixin(object):
    """Mixin for Audit subclasses.  Classes that inherit from
    this mixin will get some convenience methods for interacting with a
    lctl get_param.
    """

    def _get_param(self, *args):
        # Remove trailing newline to cleanup stdout.split("\n")
        return AgentShell.try_run(["lctl", "get_param"] + [x.replace("/", ".") for x in args])

    def get_param_lines(self, path, filter_f=None):
        """Return a generator for stripped lines read from the param.

        If the optional filter_f argument is supplied, it will be applied
        prior to stripping each line.
        """
        stdout = self._get_param("-n", path).strip()

        if stdout:
            for line in stdout.split("\n"):
                if filter_f:
                    if filter_f(line):
                        yield line
                else:
                    yield line

    def get_param_raw(self, path):
        return self._get_param("-n", path)

    def get_param_string(self, path):
        """Read the first line from a param and return it as a string."""
        return self.get_param_lines(path).next()

    def get_param_int(self, path):
        """Read one line from a param and return it as an int."""
        return int(self.get_param_string(path))

    def join_param(self, a, *p):
        if a:
            arr = [a]
        else:
            arr = []
        for x in p:
            arr.append(x)
        return ".".join(arr)

    def list_params(self, path):
        """Return list of parameters found in path.  Or [] if none, or get_param fails."""
        try:
            return self._get_param("-N", path).strip().split("\n")
        except AgentShell.CommandExecutionError:
            return []


class FileSystemMixin(object):
    """Mixin for Audit subclasses.  Classes that inherit from
    this mixin will get some convenience methods for interacting with a
    filesystem.  The fscontext property provides a way to override the
    default filesystem context ("/") for unit testing.
    """

    # Unit tests should patch this attribute when using fixture data.
    fscontext = "/"

    def abs(self, path):
        if os.path.isabs(path):
            return os.path.join(self.fscontext, path[1:])
        else:
            return os.path.join(self.fscontext, path)

    def read_lines(self, filename, filter_f=None):
        """Return a generator for stripped lines read from the file.

        If the optional filter_f argument is supplied, it will be applied
        prior to stripping each line.
        """

        filename = self.abs(filename)

        for line in open(filename):
            if filter_f:
                if filter_f(line):
                    yield line.rstrip("\n")
            else:
                yield line.rstrip("\n")

    def read_string(self, filename):
        """Read the first line from a file and return it as a string."""
        try:
            return self.read_lines(filename).next()
        except StopIteration:
            raise RuntimeError("read_string() on empty file: %s" % filename)

    def read_int(self, filename):
        """Read one line from a file and return it as an int."""
        return int(self.read_string(filename))

    def walk(self, path):
        """Walk the supplied path. This wrapper enables simpler unit tests."""
        return os.walk(self.abs(path))
