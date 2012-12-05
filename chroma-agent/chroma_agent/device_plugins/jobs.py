#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import threading
import traceback
import sys
from chroma_agent.log import daemon_log
from chroma_agent.plugin_manager import DevicePlugin


class ActionRunnerPlugin(DevicePlugin):
    """
    This class is responsible for handling requests to run commands: invoking
    the required ActionPlugin and handling concurrency.
    """

    def __init__(self, *args, **kwargs):
        self.jobs = {}
        super(ActionRunnerPlugin, self).__init__(*args, **kwargs)

    def run(self, id, cmd, args):
        daemon_log.info("ActionRunner.run %s" % id)
        thread = JobRunner(self, id, cmd, args)
        self.jobs[id] = thread
        thread.start()

    def teardown(self):
        for job_id, thread in self.jobs.items():
            thread.stop()
            thread.join()

    def succeed(self, id, result):
        daemon_log.info("ActionRunner.succeed %s: %s" % (id, result))
        self._notify(id, result, None)
        del self.jobs[id]

    def fail(self, id, backtrace):
        daemon_log.info("ActionRunner.fail %s: %s" % (id, backtrace))
        self._notify(id, None, backtrace)
        del self.jobs[id]

    def _notify(self, id, result, backtrace):
        self.send_message(
            {
                'id': id,
                'result': result,
                'exception': backtrace
            })

    def start_session(self):
        return {
            'id': None
        }

    def on_message(self, body):
        self.run(body['id'], body['command'], body['args'])


class JobRunner(threading.Thread):
    def __init__(self, manager, id, cmd, cmd_args, *args, **kwargs):
        super(JobRunner, self).__init__(*args, **kwargs)

        self.manager = manager
        self.id = id
        self.cmd = cmd
        self.args = cmd_args

    def stop(self):
        # TODO: provide a way to abort action plugins and their child processes
        pass

    def run(self):
        daemon_log.info("JobRunner.run: %s %s %s" % (self.id, self.cmd, self.args))
        try:
            result = self.manager._session._client.action_plugins.run(self.cmd, self.args)
        except Exception:
            backtrace = '\n'.join(traceback.format_exception(*(sys.exc_info())))
            self.manager.fail(self.id, backtrace)
        else:
            self.manager.succeed(self.id, result)
