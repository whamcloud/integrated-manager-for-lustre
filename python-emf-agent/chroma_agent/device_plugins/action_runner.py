# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import threading
import traceback
import sys

from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import daemon_log
from chroma_agent.plugin_manager import DevicePlugin
from chroma_agent.agent_client import AgentDaemonContext


class CallbackAfterResponse(Exception):
    """
    Action plugins raise this to request that a callback be invoked after
    an attempt has been made to send their completion to the manager.

     1. Action runs
     2. Result sent to manager
     3. Callback runs

    """

    def __init__(self, result, callback):
        """
        :param result: Response to send back to the manager
        :param callback: To be invoked immediately before terminating the agent process
        """

        self.result = result
        self.callback = callback


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

            self._running_actions.clear()

        for thread in wait_threads:
            thread.join()

    def succeed(self, id, result, subprocesses):
        daemon_log.info("ActionRunner.succeed %s: %s" % (id, result))
        self._notify(id, result, None, subprocesses)
        with self._running_actions_lock:
            del self._running_actions[id]

    def respond_with_callback(self, id, callback_after_response, subprocesses):
        daemon_log.info("ActionRunner.respond_with_callback %s: %s" % (id, callback_after_response.result))
        self._notify(
            id,
            callback_after_response.result,
            None,
            subprocesses,
            callback_after_response.callback,
        )
        with self._running_actions_lock:
            del self._running_actions[id]

    def fail(self, id, backtrace, subprocesses):
        daemon_log.info("ActionRunner.fail %s: %s" % (id, backtrace))
        self._notify(id, None, backtrace, subprocesses)
        with self._running_actions_lock:
            del self._running_actions[id]

    def cancelled(self, id):
        """
        Action completed due to SubprocessAborted exception (raise when
        an action is cancelled)
        """
        if not self._tearing_down:
            daemon_log.info("ActionRunner.cancelled %s" % id)
            with self._running_actions_lock:
                del self._running_actions[id]

    def _notify(self, id, result, backtrace, subprocesses, callback=None):
        if self._tearing_down:
            return

        self.send_message(
            {
                "type": "ACTION_COMPLETE",
                "id": id,
                "result": result,
                "exception": backtrace,
                "subprocesses": subprocesses,
            },
            callback,
        )

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
        if body["type"] == "ACTION_START":
            self.run(body["id"], body["action"], body["args"])
        elif body["type"] == "ACTION_CANCEL":
            self.cancel(body["id"])
        else:
            raise NotImplementedError("Unknown type '%s'" % body["type"])


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
        self._subprocess_abort = AgentShell.thread_state.abort

        # We are now stoppable
        self._started.set()

        daemon_log.info("%s.run: %s %s %s" % (self.__class__.__name__, self.id, self.action, self.args))
        try:
            AgentShell.thread_state.enable_save()

            agent_daemon_context = AgentDaemonContext(self.manager._session._client.sessions._sessions)

            result = self.manager._session._client.action_plugins.run(self.action, agent_daemon_context, self.args)
        except CallbackAfterResponse as e:
            self.manager.respond_with_callback(self.id, e, AgentShell.thread_state.get_subprocesses())
        except AgentShell.SubprocessAborted:
            self.manager.cancelled(self.id)
        except Exception:
            backtrace = "\n".join(traceback.format_exception(*(sys.exc_info())))

            self.manager.fail(self.id, backtrace, AgentShell.thread_state.get_subprocesses())
        else:
            self.manager.succeed(self.id, result, AgentShell.thread_state.get_subprocesses())
