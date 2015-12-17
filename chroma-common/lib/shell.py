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


import subprocess
import os
import tempfile
import collections
import time
import warnings


class Shell(object):
    class CommandExecutionError(Exception):
        def __init__(self, result, command):
            self.result = result
            self.command = " ".join(command)

        def __str__(self):
            return "Error (%s) running '%s': '%s' '%s'" % (self.result.rc, self.command,
                                                           self.result.stdout, self.result.stderr)

        # Keeping for backwards compatibility, will be removed over time.
        @property
        def rc(self):
            warnings.warn("Direct use of rc in CommandExecutionError is deprecated", DeprecationWarning)
            return self.result.rc

        @property
        def stdout(self):
            warnings.warn("Direct use of stdout in CommandExecutionError is deprecated", DeprecationWarning)
            return self.result.stdout

        @property
        def stderr(self):
            warnings.warn("Direct use of stderr in CommandExecutionError is deprecated", DeprecationWarning)
            return self.result.stderr

    # Effectively no autotimeout for commands.
    SHELLTIMEOUT = 0xfffffff

    RunResult = collections.namedtuple("RunResult", ['rc', 'stdout', 'stderr', 'timeout'])

    @classmethod
    def _run(cls, arg_list, logger, monitor_func, timeout):
        """
        Separate the bare inner of running a command, so that tests can
        stub this function while retaining the related behaviour of run()
        """

        # Popen has a limit of 2^16 for the output if you use subprocess.PIPE (as we did recently) so use real files so
        # the output side is effectively limitless

        stdout_fd = tempfile.TemporaryFile()
        stderr_fd = tempfile.TemporaryFile()

        try:
            p = subprocess.Popen(arg_list,
                                 stdout = stdout_fd,
                                 stderr = stderr_fd,
                                 close_fds = True)

            # Rather than using p.wait(), we do a slightly more involved poll/backoff, in order
            # to poll the thread_state.teardown event as well as the completion of the subprocess.
            # This is done to allow cancellation of subprocesses
            rc = None
            max_wait = 1.0
            wait = 1.0E-3
            timeout += time.time()
            while rc is None:
                rc = p.poll()
                if rc is None:
                    if monitor_func:
                        monitor_func(p, arg_list, logger)

                    time.sleep(1)

                    if time.time() > timeout:
                        p.kill()
                        stdout_fd.seek(0)
                        stderr_fd.seek(0)
                        return cls.RunResult(254, stdout_fd.read(), stderr_fd.read(), True)
                    elif wait < max_wait:
                        wait *= 2.0
                else:
                    stdout_fd.seek(0)
                    stderr_fd.seek(0)
                    return cls.RunResult(rc, stdout_fd.read(), stderr_fd.read(), False)
        finally:
            stdout_fd.close()
            stderr_fd.close()

    @classmethod
    def run(cls, arg_list, logger=None, monitor_func=None, timeout=SHELLTIMEOUT):
        """Run a subprocess, and return a tuple of rc, stdout, stderr.
        Record subprocesses run and their results in log.

        Note: we buffer all output, so do not run subprocesses with large outputs
        using this function.
        """

        # TODO: add a 'quiet' flag and use it from spammy/polling plugins to avoid
        # sending silly amounts of command output back to the manager.
        if logger:
            logger.debug("Shell.run: %s" % repr(arg_list))

        os.environ["TERM"] = ""

        result = Shell._run(arg_list, logger, monitor_func, timeout)

        return result

    @classmethod
    def try_run(cls, arg_list, logger=None, monitor_func=None, timeout=SHELLTIMEOUT):
        """Run a subprocess, and raise an exception if it returns nonzero.  Return
        stdout string.
        """

        result = Shell.run(arg_list, logger, monitor_func, timeout)

        if result.rc != 0:
            raise Shell.CommandExecutionError(result, arg_list)

        return result.stdout

    @classmethod
    def run_canned_error_message(cls, arg_list):
        """
        Run a shell command return None is successful, or User Error message if not
        :param args:
        :return: None if successful or canned user error message
        """
        result = Shell.run(arg_list)

        if result.rc != 0:
            return "Error (%s) running '%s': '%s' '%s'" % (result.rc, " ".join(arg_list),
                                                           result.stdout, result.stderr)

        return None
