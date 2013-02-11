#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import threading
import traceback
import sys
from chroma_agent import shell
from chroma_agent.log import daemon_log
from chroma_agent.plugin_manager import DevicePlugin
from chroma_agent.shell import SubprocessAborted


class ActionRunnerPlugin(DevicePlugin):
    """
    This class is responsible for handling requests to run actions: invoking
    the required ActionPlugin and handling concurrency.
    """

    def __init__(self, *args, **kwargs):
        self._running_actions_lock = threading.Lock()
        self._running_actions = {}
        self._tearing_down = False
        super(ActionRunnerPlugin, self).__init__(*args, **kwargs)

    def run(self, id, cmd, args):
        daemon_log.info("ActionRunner.run %s" % id)
        thread = ActionRunner(self, id, cmd, args)
        with self._running_actions_lock:
            if not self._tearing_down:
                self._running_actions[id] = thread
                thread.start()

    def teardown(self):
        self._tearing_down = True

        wait_threads = []
        with self._running_actions_lock:
            for action_id, thread in self._running_actions.items():
                thread.stop()
                wait_threads.append(thread)

        for thread in wait_threads:
            thread.join()

    def succeed(self, id, result, subprocesses):
        daemon_log.info("ActionRunner.succeed %s: %s" % (id, result))
        self._notify(id, result, None, subprocesses)
        with self._running_actions_lock:
            del self._running_actions[id]

    def fail(self, id, backtrace, subprocesses):
        daemon_log.info("ActionRunner.fail %s: %s" % (id, backtrace))
        self._notify(id, None, backtrace, subprocesses)
        with self._running_actions_lock:
            del self._running_actions[id]

    def cancelled(self, id):
        daemon_log.info("ActionRunner.cancelled %s" % id)
        with self._running_actions_lock:
            del self._running_actions[id]

    def _notify(self, id, result, backtrace, subprocesses):
        if self._tearing_down:
            return

        self.send_message(
            {
                'type': "ACTION_COMPLETE",
                'id': id,
                'result': result,
                'exception': backtrace,
                'subprocesses': subprocesses
            })

    def cancel(self, id):
        with self._running_actions_lock:
            try:
                thread = self._running_actions[id]
            except KeyError:
                # Cannot cancel that which does not exist
                pass
            else:
                thread.stop()

    def on_message(self, body):
        if body['type'] == 'ACTION_START':
            self.run(body['id'], body['action'], body['args'])
        elif body['type'] == 'ACTION_CANCEL':
            self.cancel(body['id'])
        else:
            raise NotImplementedError("Unknown type '%s'" % body['type'])


class ActionRunner(threading.Thread):
    def __init__(self, manager, id, action, cmd_args, *args, **kwargs):
        super(ActionRunner, self).__init__(*args, **kwargs)

        self.manager = manager
        self.id = id
        self.action = action
        self.args = cmd_args

        self._subprocess_abort = None
        self._started = threading.Event()

    def stop(self):
        # Don't go any further until the run() method has set up its thread local state
        self._started.wait()

        # If the action is in a subprocess, this will cause it to raise an exception
        self._subprocess_abort.set()

    def run(self):
        # Grab a reference to the thread-local state for this thread and put
        # it somewhere that other threads can see it, so that we can be signalled
        # to shut down
        self._subprocess_abort = shell.thread_state.abort

        # We are now stoppable
        self._started.set()

        daemon_log.info("%s.run: %s %s %s" % (self.__class__.__name__, self.id, self.action, self.args))
        try:
            shell.thread_state.enable_save()
            result = self.manager._session._client.action_plugins.run(self.action, self.args)
        except SubprocessAborted:
            self.manager.cancelled(self.id)
        except Exception:
            backtrace = '\n'.join(traceback.format_exception(*(sys.exc_info())))

            self.manager.fail(self.id, backtrace, shell.thread_state.get_subprocesses())
        else:
            self.manager.succeed(self.id, result, shell.thread_state.get_subprocesses())
