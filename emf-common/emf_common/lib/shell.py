# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import subprocess
import os
import tempfile
import collections
import time
import warnings


class BaseShell(object):
    class CommandExecutionError(Exception):
        def __init__(self, result, command):
            self.result = result
            self.command = " ".join(command)

        def __str__(self):
            return "Error (%s) running '%s': '%s' '%s'" % (
                self.result.rc,
                self.command,
                self.result.stdout,
                self.result.stderr,
            )

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
    SHELLTIMEOUT = 0xFFFFFFF

    RunResult = collections.namedtuple("RunResult", ["rc", "stdout", "stderr", "timeout"])

    @classmethod
    def _run(cls, arg_list, logger, monitor_func, timeout, shell=False):
        """Separate the bare inner of running a command, so that tests can
        stub this function while retaining the related behaviour of run()
        """

        assert type(arg_list) in [list, str, unicode], "arg list must be list or str :%s" % type(arg_list)

        # Allow simple commands to just be presented as a string. However do not start formatting the string this
        # will be rejected in a code review. If it has args present them as a list.
        if type(arg_list) in [str, unicode]:
            arg_list = arg_list.split()

        # Popen has a limit of 2^16 for the output if you use subprocess.PIPE (as we did recently) so use real files so
        # the output side is effectively limitless
        stdout_fd = tempfile.TemporaryFile()
        stderr_fd = tempfile.TemporaryFile()

        try:
            p = subprocess.Popen(arg_list, stdout=stdout_fd, stderr=stderr_fd, close_fds=True, shell=shell)

            # Rather than using p.wait(), we do a slightly more involved poll/backoff, in order
            # to poll the thread_state.teardown event as well as the completion of the subprocess.
            # This is done to allow cancellation of subprocesses
            rc = None
            max_wait = 1.0
            wait = 1.0e-3
            timeout += time.time()
            while rc is None:
                rc = p.poll()
                if rc is None:
                    if monitor_func:
                        monitor_func(p, arg_list, logger)

                    time.sleep(wait)

                    if time.time() > timeout:
                        p.kill()
                        stdout_fd.seek(0)
                        stderr_fd.seek(0)
                        return cls.RunResult(
                            254,
                            stdout_fd.read().decode("ascii", "ignore"),
                            stderr_fd.read().decode("ascii", "ignore"),
                            True,
                        )
                    elif wait < max_wait:
                        wait *= 2.0
                else:
                    stdout_fd.seek(0)
                    stderr_fd.seek(0)
                    return cls.RunResult(
                        rc,
                        stdout_fd.read().decode("ascii", "ignore"),
                        stderr_fd.read().decode("ascii", "ignore"),
                        False,
                    )
        finally:
            stdout_fd.close()
            stderr_fd.close()

    @classmethod
    def run(cls, arg_list, logger=None, monitor_func=None, timeout=SHELLTIMEOUT, shell=False):
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

        result = cls._run(arg_list, logger, monitor_func, timeout, shell=shell)

        return result

    @classmethod
    def try_run(cls, arg_list, logger=None, monitor_func=None, timeout=SHELLTIMEOUT, shell=False):
        """Run a subprocess, and raise an exception if it returns nonzero.  Return
        stdout string.
        """

        result = cls.run(arg_list, logger, monitor_func, timeout, shell=shell)

        if result.rc != 0:
            raise cls.CommandExecutionError(result, arg_list)

        return result.stdout

    @classmethod
    def run_canned_error_message(cls, arg_list):
        """
        Run a shell command return None is successful, or User Error message if not
        :param args:
        :return: None if successful or canned user error message
        """
        result = cls.run(arg_list)

        if result.rc != 0:
            return "Error (%s) running '%s': '%s' '%s'" % (result.rc, " ".join(arg_list), result.stdout, result.stderr)

        return None


# By default Shell is this BaseShell class, and other emf_common modules use BaseShell via Shell by default.
# However consumers (namely the agent today) may change Shell to reference their own SubClass version and this will
# mean that emf_common consumers of Shell use the SubClass rather than the base.
Shell = BaseShell


def set_shell(new_shell_class):
    """
    Change the Shell the emf_common (and any other referencers of Shell in this module) use for Shell commands
    :param new_shell_class: The new Shell classs to use
    """
    global Shell
    Shell = new_shell_class
