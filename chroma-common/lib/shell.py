#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from StringIO import StringIO
from copy import deepcopy
import subprocess
import threading
import os

logger = None


class CommandExecutionError(Exception):
    def __init__(self, rc, command, stdout, stderr):
        self.rc = rc
        self.command = " ".join(command)
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        return "Error (%s) running '%s': '%s' '%s'" % (self.rc, self.command,
                                                       self.stdout, self.stderr)


class ThreadState(threading.local):
    """Thread-local logs for stdout/stderr from wrapped commands"""

    def __init__(self):
        self._save = False
        self._subprocesses = []
        self.messages_buf = StringIO()
        self.abort = threading.Event()

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
thread_state = ThreadState()


class SubprocessAborted(Exception):
    pass


def set_logger(_logger):
    global logger
    logger = _logger


def _run(arg_list):
    """
    Separate the bare inner of running a command, so that tests can
    stub this function while retaining the related behaviour of run()
    """
    p = subprocess.Popen(arg_list,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        close_fds = True)

    # Rather than using p.wait(), we do a slightly more involved poll/backoff, in order
    # to poll the thread_state.teardown event as well as the completion of the subprocess.
    # This is done to allow cancellation of subprocesses
    rc = None
    min_wait = 1.0E-3
    max_wait = 1.0
    wait = min_wait
    while rc is None:
        rc = p.poll()
        if rc is None:
            thread_state.abort.wait(timeout = wait)
            if thread_state.abort.is_set():
                if logger:
                    logger.warning("Teardown: killing subprocess %s (%s)" % (p.pid, arg_list))
                p.kill()
                raise SubprocessAborted()
            elif wait < max_wait:
                wait *= 2.0
        else:
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
    if logger:
        logger.debug("shell.run: %s" % repr(arg_list))

    os.environ["TERM"] = ""

    rc, stdout_buf, stderr_buf = _run(arg_list)

    thread_state.save_result(arg_list, rc, stdout_buf, stderr_buf)

    return rc, stdout_buf, stderr_buf


def try_run(arg_list):
    """Run a subprocess, and raise an exception if it returns nonzero.  Return
    stdout string."""

    rc, stdout, stderr = run(arg_list)
    if rc != 0:
        raise CommandExecutionError(rc, arg_list, stdout, stderr)

    return stdout
