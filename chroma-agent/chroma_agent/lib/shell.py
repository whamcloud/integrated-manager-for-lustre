# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import logging
from StringIO import StringIO
from copy import deepcopy
import threading

from iml_common.lib.shell import BaseShell
from iml_common.lib.shell import set_shell

console_log = logging.getLogger('console')


class ResultStore(threading.local):
    """
    Allow storage of the results of shell commands in a thread safe manner.

    Also provides for the abort of running commands using the abort event. Which does slightly
    overload this class, but we can't rebuild Rome in a day.
    """

    def __init__(self):
        super(ResultStore, self).__init__()

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

    def save_result(self, arg_list, result):
        """
        Add a RunResult to the subprocess results
        :arg arglist is the list of arguments making up the command.
        :arg result is the RunResult of the command.
        """
        if self._save:
            self._subprocesses.append({
                'args': arg_list,
                'rc': result.rc,
                'stdout': result.stdout,
                'stderr': result.stderr
            })


class AgentShell(BaseShell):
    class SubprocessAborted(Exception):
        pass

    thread_state = ResultStore()

    # This log is for messages about operations invoked at the user's request,
    # the user will be interested general breezy chat (INFO) about what we're
    # doing for them

    @classmethod
    def monitor_func(cls, process, arg_list, logger):
        if AgentShell.thread_state.abort.is_set():
            if logger:
                logger.warning("Teardown: killing subprocess %s (%s)" % (process.pid, arg_list))
            process.kill()
            raise AgentShell.SubprocessAborted()

    @classmethod
    def run(cls, arg_list):
        """
        Run a subprocess, and return a named tuple of rc, stdout, stderr.
        Record subprocesses run and their results in log.

        Note: we buffer all output, so do not run subprocesses with large outputs
        using this function.
        """

        result = super(AgentShell, cls).run(arg_list, console_log, cls.monitor_func)

        cls.thread_state.save_result(arg_list, result)

        return result

    @classmethod
    def run_old(cls, arg_list):
        """ This method is provided for backwards compatibility only, use run() in new code """
        result = AgentShell.run(arg_list)

        return result.rc, result.stdout, result.stderr

    @classmethod
    def try_run(cls, arg_list):
        """ Run a subprocess, and raise an exception if it returns nonzero.  Return stdout string. """

        result = AgentShell.run(arg_list)

        if result.rc != 0:
            raise AgentShell.CommandExecutionError(result, arg_list)

        return result.stdout

    @classmethod
    def run_canned_error_message(cls, arg_list):
        """
        Run a shell command return None is successful, or User Error message if not

        :return: None if successful or canned user error message
        """
        result = AgentShell.run(arg_list)

        if result.rc != 0:
            return "Error (%s) running '%s': '%s' '%s'" % (result.rc, " ".join(arg_list), result.stdout, result.stderr)

        return None

# We want iml_common routines to use our AgentShell.
set_shell(AgentShell)
