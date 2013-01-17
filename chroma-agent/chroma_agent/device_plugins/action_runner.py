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
    This class is responsible for handling requests to run actions: invoking
    the required ActionPlugin and handling concurrency.
    """

    def __init__(self, *args, **kwargs):
        self.running_actions = {}
        super(ActionRunnerPlugin, self).__init__(*args, **kwargs)

    def run(self, id, cmd, args):
        daemon_log.info("ActionRunner.run %s" % id)
        thread = ActionRunner(self, id, cmd, args)
        self.running_actions[id] = thread
        thread.start()

    def teardown(self):
        for action_id, thread in self.running_actions.items():
            thread.stop()
            thread.join()

    def succeed(self, id, result):
        daemon_log.info("ActionRunner.succeed %s: %s" % (id, result))
        self._notify(id, result, None)
        del self.running_actions[id]

    def fail(self, id, backtrace):
        daemon_log.info("ActionRunner.fail %s: %s" % (id, backtrace))
        self._notify(id, None, backtrace)
        del self.running_actions[id]

    def _notify(self, id, result, backtrace):
        self.send_message(
            {
                'id': id,
                'result': result,
                'exception': backtrace
            })

    def on_message(self, body):
        self.run(body['id'], body['action'], body['args'])


class ActionRunner(threading.Thread):
    def __init__(self, manager, id, action, cmd_args, *args, **kwargs):
        super(ActionRunner, self).__init__(*args, **kwargs)

        self.manager = manager
        self.id = id
        self.action = action
        self.args = cmd_args

    def stop(self):
        # TODO: provide a way to abort action plugins and their child processes
        pass

    def run(self):
        daemon_log.info("%s.run: %s %s %s" % (self.__class__.__name__, self.id, self.action, self.args))
        try:
            result = self.manager._session._client.action_plugins.run(self.action, self.args)
        except Exception:
            backtrace = '\n'.join(traceback.format_exception(*(sys.exc_info())))
            self.manager.fail(self.id, backtrace)
        else:
            self.manager.succeed(self.id, result)
