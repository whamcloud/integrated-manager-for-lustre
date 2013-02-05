#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from StringIO import StringIO
from copy import deepcopy
import logging
import subprocess
import threading
import os

from chroma_agent.log import console_log


class ThreadLogs(threading.local):
    """Thread-local logs for stdout/stderr from wrapped commands"""
    def __init__(self):
        self.commands = []
        self.messages_buf = StringIO()

        self.messages = logging.getLogger("%s" % threading.current_thread().ident)
        self.messages.addHandler(logging.StreamHandler(self.messages_buf))

    def get_commands(self):
        """Return a non-thread-local copy of the commands"""
        return deepcopy(self.commands)

    def save_result(self, arg_list, rc, stdout, stderr):
        self.commands.append({
            'args': arg_list,
            'rc': rc,
            'stdout': stdout,
            'stderr': stderr
        })


logs = ThreadLogs()

log = logs.messages


def _run(arg_list, shell):
    """
    Separate the bare inner of running a command, so that tests can
    stub this function while retaining the related behaviour of run()
    """
    p = subprocess.Popen(arg_list, shell = shell,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        close_fds = True)
    rc = p.wait()
    stdout_buf, stderr_buf = p.communicate()

    return rc, stdout_buf, stderr_buf


def run(arg_list, shell = False):
    """Run a subprocess, and return a tuple of rc, stdout, stderr.
    Record commands run and their results in log.

    Note: we buffer all output, so do not run commands with large outputs
    using this function.
    """

    # TODO: add a 'quiet' flag and use it from spammy/polling plugins to avoid
    # sending silly amounts of command output back to the manager.

    console_log.debug("shell.run: %s" % arg_list)
    os.environ["TERM"] = ""

    rc, stdout_buf, stderr_buf = _run(arg_list, shell)

    logs.save_result(arg_list, rc, stdout_buf, stderr_buf)

    return rc, stdout_buf, stderr_buf


def try_run(arg_list, shell = False):
    """Run a subprocess, and raise an exception if it returns nonzero.  Return
    stdout string."""

    rc, stdout, stderr = run(arg_list, shell)
    if rc != 0:
        raise RuntimeError("Error (%s) running '%s': '%s' '%s'" % (rc, " ".join(arg_list), stdout, stderr))

    return stdout
