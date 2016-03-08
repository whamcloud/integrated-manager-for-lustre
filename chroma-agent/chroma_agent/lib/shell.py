#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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


import logging
from StringIO import StringIO
from copy import deepcopy
import threading

from chroma_agent.chroma_common.lib.shell import Shell

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


class AgentShell(Shell):
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
    def run_new(cls, arg_list):
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
    def run(cls, arg_list):
        """ This method is provided for backwards compatibility only, use run_new() in new code """
        result = AgentShell.run_new(arg_list)

        return result.rc, result.stdout, result.stderr

    @classmethod
    def try_run(cls, arg_list):
        """ Run a subprocess, and raise an exception if it returns nonzero.  Return stdout string. """

        result = AgentShell.run_new(arg_list)

        if result.rc != 0:
            raise AgentShell.CommandExecutionError(result, arg_list)

        return result.stdout

    @classmethod
    def run_canned_error_message(cls, arg_list):
        """
        Run a shell command return None is successful, or User Error message if not

        :return: None if successful or canned user error message
        """
        result = AgentShell.run_new(arg_list)

        if result.rc != 0:
            return "Error (%s) running '%s': '%s' '%s'" % (result.rc, " ".join(arg_list), result.stdout, result.stderr)

        return None
