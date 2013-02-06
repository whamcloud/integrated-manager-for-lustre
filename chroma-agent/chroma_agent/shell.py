#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from StringIO import StringIO
from copy import deepcopy
import subprocess
import threading
import os

from chroma_agent.log import console_log


class ThreadLogs(threading.local):
    """Thread-local logs for stdout/stderr from wrapped commands"""

    def __init__(self):
        self._save = False
        self._subprocesses = []
        self.messages_buf = StringIO()

    def enable_save(self):
        """
        Enable recording of all subprocesses run in this thread
        """
        self._save = True

    def get_subprocesses(self):
        """Return a non-thread-local copy of the subprocesses"""
        return deepcopy(self._subprocesses)

    def save_result(self, arg_list, rc, stdout, stderr):
        if self._save:
            self._subprocesses.append({
                'args': arg_list,
                'rc': rc,
                'stdout': stdout,
                'stderr': stderr
            })

# The logging state for this thread
logs = ThreadLogs()


def _run(arg_list):
    """
    Separate the bare inner of running a command, so that tests can
    stub this function while retaining the related behaviour of run()
    """
    p = subprocess.Popen(arg_list,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        close_fds = True)
    rc = p.wait()
    stdout_buf, stderr_buf = p.communicate()

    return rc, stdout_buf, stderr_buf


def run(arg_list):
    """Run a subprocess, and return a tuple of rc, stdout, stderr.
    Record subprocesses run and their results in log.

    Note: we buffer all output, so do not run subprocesses with large outputs
    using this function.
    """

    # TODO: add a 'quiet' flag and use it from spammy/polling plugins to avoid
    # sending silly amounts of command output back to the manager.

    console_log.debug("shell.run: %s" % arg_list)
    os.environ["TERM"] = ""

    rc, stdout_buf, stderr_buf = _run(arg_list)

    logs.save_result(arg_list, rc, stdout_buf, stderr_buf)

    return rc, stdout_buf, stderr_buf


def try_run(arg_list):
    """Run a subprocess, and raise an exception if it returns nonzero.  Return
    stdout string."""

    rc, stdout, stderr = run(arg_list)
    if rc != 0:
        raise RuntimeError("Error (%s) running '%s': '%s' '%s'" % (rc, " ".join(arg_list), stdout, stderr))

    return stdout
