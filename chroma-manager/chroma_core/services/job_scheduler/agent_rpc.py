#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from collections import defaultdict
import json
import threading
import time
import uuid
from chroma_core.services import log_register, ServiceThread
from chroma_core.services.http_agent.sessions import AgentSessionRpc
from chroma_core.services.http_agent.queues import AgentTxQueue
from chroma_core.services.queue import AgentRxQueue
from chroma_core.services.rpc import RpcTimeout


log = log_register(__name__)

# The name of the device plugin on the agent with which
# this module will communicate
ACTION_MANAGER_PLUGIN_NAME = 'action_runner'

# If no action_runner session is present when trying to run
# an action, wait this long for one to show up
SESSION_WAIT_TIMEOUT = 10


class AgentRunnerPluginRxQueue(AgentRxQueue):
    plugin = ACTION_MANAGER_PLUGIN_NAME


class ActionInFlight(object):
    def __init__(self, session_id, fqdn, action, args):
        self.id = uuid.uuid4().__str__()
        self.session_id = session_id
        self.fqdn = fqdn

        self.action = action
        self.args = args

        self.complete = threading.Event()
        self.exception = None
        self.result = None
        self.subprocesses = []

    def get_request(self):
        return {
            'fqdn': self.fqdn,
            'type': 'DATA',
            'plugin': ACTION_MANAGER_PLUGIN_NAME,
            'session_id': self.session_id,
            'session_seq': None,
            'body': {
                'type': 'ACTION_START',
                'id': self.id,
                'action': self.action,
                'args': self.args
            }
        }

    def get_cancellation(self):
        return {
            'fqdn': self.fqdn,
            'type': 'DATA',
            'plugin': ACTION_MANAGER_PLUGIN_NAME,
            'session_id': self.session_id,
            'session_seq': None,
            'body': {
                'type': 'ACTION_CANCEL',
                'id': self.id,
                'action': None,
                'args': None
            }
        }


class AgentRpcMessenger(object):
    """
    This class consumes AgentRunnerPluginRxQueue, sends
    messages to AgentTxQueue, and maintains state for
    actions in progress.
    """

    def __init__(self):
        super(AgentRpcMessenger, self).__init__()

        # session to list of RPC IDs
        self._session_rpcs = defaultdict(dict)

        # FQDN to session
        self._sessions = {}

        self._action_runner_rx_queue = AgentRunnerPluginRxQueue()

        self._lock = threading.Lock()

    def run(self):
        try:
            AgentSessionRpc().reset_plugin_sessions(ACTION_MANAGER_PLUGIN_NAME)
        except RpcTimeout:
            # Assume this means that the http_agent service isn't running: this
            # is acceptable, as our goal of there not being any sessions is
            # already the case.
            log.warning("Unable to reset %s sessions" % ACTION_MANAGER_PLUGIN_NAME)

        self._action_runner_rx_queue.purge()
        self._action_runner_rx_queue.serve(session_callback = self.on_rx)
        log.info("AgentRpcMessenger.complete")

    def stop(self):
        log.info("AgentRpcMessenger.stop")
        self._action_runner_rx_queue.stop()

    def complete_all(self):
        log.info("AgentRpcMessenger.complete_all")
        for session_id, rpc_id_to_rpc in self._session_rpcs.items():
            for rpc_id, rpc_state in rpc_id_to_rpc.items():
                log.info("AgentRpcMessenger.complete_all: erroring %s" % rpc_state.id)
                if not rpc_state.complete.is_set():
                    rpc_state.exception = "Cancelled due to service shutdown"
                    rpc_state.complete.set()

    def remove(self, fqdn):
        with self._lock:
            try:
                del self._sessions[fqdn]
            except KeyError:
                pass

    def on_rx(self, message):
        with self._lock:
            log.debug("on_rx: %s" % message)
            fqdn = message['fqdn']
            session_id = message['session_id']
            log.info("AgentRpcMessenger.on_rx: %s/%s" % (fqdn, session_id))

            def abort_session(old_session_id, new_session_id = None):
                log.warning("AgentRpcMessenger.on_rx: aborting session %s" % old_session_id)
                old_rpcs = self._session_rpcs[old_session_id]
                self._sessions[fqdn] = new_session_id
                for rpc in old_rpcs.values():
                    if new_session_id:
                        log.warning("AgentRpcMessenger.on_rx: re-issuing RPC %s for session %s (was %s)" % (
                            rpc.id, new_session_id, old_session_id))
                        rpc.session_id = new_session_id
                        self._resend(rpc)
                    else:
                        rpc.exception = "Communications error with %s" % fqdn
                        rpc.complete.set()
                del self._session_rpcs[old_session_id]

            if message['type'] == 'SESSION_CREATE':
                if fqdn in self._sessions:
                    old_session_id = self._sessions[fqdn]
                    abort_session(old_session_id, session_id)
                else:
                    self._sessions[fqdn] = session_id
            elif message['type'] == 'SESSION_TERMINATE':
                # An agent has timed out or restarted, we're being told its session is now dead
                if message['fqdn'] in self._sessions:
                    abort_session(message['session_id'])
            elif message['type'] == 'SESSION_TERMINATE_ALL':
                # The http_agent service has restarted, all sessions are now over
                for session in self._sessions.values():
                    abort_session(session)
            else:
                rpc_response = message['body']
                if rpc_response['type'] != 'ACTION_COMPLETE':
                    log.error("Unexpected type '%s'" % rpc_response['type'])
                    return

                if fqdn in self._sessions and self._sessions[fqdn] != session_id:
                    log.info("AgentRpcMessenger.on_rx: cancelling session %s/%s (replaced by %s)" % (fqdn, self._sessions[fqdn], session_id))
                    abort_session(self._sessions[fqdn])
                    AgentSessionRpc().reset_session(fqdn, ACTION_MANAGER_PLUGIN_NAME, session_id)
                elif fqdn in self._sessions:
                    log.info("AgentRpcMessenger.on_rx: good session %s/%s" % (fqdn, session_id))
                    # Find this RPC and complete it
                    rpc = self._session_rpcs[session_id][rpc_response['id']]
                    del self._session_rpcs[session_id][rpc_response['id']]
                    rpc.exception = rpc_response['exception']
                    rpc.result = rpc_response['result']
                    rpc.subprocesses = rpc_response['subprocesses']
                    log.info("AgentRpcMessenger.on_rx: completing rpc %s" % rpc.id)
                    rpc.complete.set()
                else:
                    log.info("AgentRpcMessenger.on_rx: unknown session %s/%s" % (fqdn, session_id))
                    # A session I never heard of?
                    AgentSessionRpc().reset_session(fqdn, ACTION_MANAGER_PLUGIN_NAME, session_id)

    def _resend(self, rpc):
        log.debug("AgentRpcMessenger._resend: rpc %s in session %s" % (rpc.id, rpc.session_id))
        self._session_rpcs[rpc.session_id][rpc.id] = rpc
        AgentTxQueue().put(rpc.get_request())

    def _send_request(self, fqdn, action, args):
        wait_count = 0

        while not fqdn in self._sessions:
            # Allow a short wait for a session to show up, for example
            # when running setup actions on a host we've just added its
            # session may not yet have been fully established
            log.error("AgentRpcMessenger._send: no session for %s" % fqdn)
            wait_count += 1
            time.sleep(1)
            if wait_count > SESSION_WAIT_TIMEOUT:
                raise AgentException(fqdn, action, args, "No %s session for %s" % (ACTION_MANAGER_PLUGIN_NAME, fqdn))

        with self._lock:
            session_id = self._sessions[fqdn]
            log.debug("AgentRpcMessenger._send: using session %s" % session_id)

            rpc = ActionInFlight(session_id, fqdn, action, args)

            self._session_rpcs[session_id][rpc.id] = rpc
            AgentTxQueue().put(rpc.get_request())
            return rpc

    def _send_cancellation(self, rpc):
        with self._lock:
            try:
                self._session_rpcs[rpc.session_id][rpc.id]
            except KeyError:
                log.warning("Dropping cancellation of RPC %s, it is already complete or aborted" % rpc.id)
            else:
                log.warning("Cancelling RPC %s" % rpc.id)
                AgentTxQueue().put(rpc.get_cancellation())
                del self._session_rpcs[rpc.session_id][rpc.id]

    def _complete(self, rpc, cancel_event):
        log.info("AgentRpcMessenger._complete: starting wait for rpc %s" % rpc.id)

        # Wait for rpc.complete, waking up every second to
        # check cancel_event
        while True:
            if cancel_event.is_set():
                self._send_cancellation(rpc)
                raise AgentCancellation()
            else:
                rpc.complete.wait(timeout = 1.0)
                if rpc.complete.is_set():
                    break

        log.info("AgentRpcMessenger._complete: completed wait for rpc %s" % rpc.id)
        if rpc.exception:
            raise AgentException(rpc.fqdn, rpc.action, rpc.args, rpc.exception, subprocesses = rpc.subprocesses)
        else:
            return rpc.result

    def call(self, fqdn, action, args, cancel_event):
        log.debug("AgentRpcMessenger.call: %s %s" % (fqdn, action))
        rpc = self._send_request(fqdn, action, args)
        return self._complete(rpc, cancel_event), rpc


class AgentRpc(object):
    """
    This class exists to provide one-per-process initialization of
    AgentRpcMessenger
    """
    thread = None
    _messenger = None

    @classmethod
    def start(cls):
        cls._messenger = AgentRpcMessenger()
        cls.thread = ServiceThread(cls._messenger)
        cls.thread.start()

    @classmethod
    def shutdown(cls):
        if cls.thread is not None:
            cls.thread.stop()
            cls.thread.join()
            cls._messenger.complete_all()

    @classmethod
    def call(cls, fqdn, action, args, cancel_event):
        return cls._messenger.call(fqdn, action, args, cancel_event)

    @classmethod
    def remove(cls, fqdn):
        return cls._messenger.remove(fqdn)


class AgentCancellation(Exception):
    pass


class AgentException(Exception):
    def __init__(self, fqdn, action, params, backtrace, subprocesses = []):
        self.fqdn = fqdn
        self.action = action
        self.params = params
        self.backtrace = backtrace
        self.subprocesses = subprocesses

    def __str__(self):
        return """AgentException
Host: %s
Action: %s
Arguments: %s
Exception: %s
""" % (self.fqdn, self.action, self.params, self.backtrace)


class AgentSsh(object):
    """
    This class can run agent actions over SSH (as opposed to the usual
    way of running actions over reverse-HTTPS).
    """
    def __init__(self, address, log = None, console_callback = None, timeout = None):
        DEFAULT_TIMEOUT = 60
        if timeout:
            self.timeout = timeout
        else:
            self.timeout = DEFAULT_TIMEOUT

        self.address = address

        self.console_callback = console_callback

        if log:
            self.log = log
        else:
            import logging
            self.log = logging.getLogger(None)

    DEFAULT_USERNAME = 'root'

    def console_append(self, chunk):
        if self.console_callback:
            self.console_callback(chunk)

    def ssh_params(self):
        if self.address.find("@") != -1:
            user, host = self.address.split("@")
        else:
            user = self.DEFAULT_USERNAME
            host = self.address

        if host.find(":") != -1:
            host, port = host.split(":")
        else:
            port = None

        return user, host, port

    def ssh(self, command):
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # How long it may take to establish a TCP connection
        SOCKET_TIMEOUT = self.timeout
        # How long it may take to get the output of our agent
        # (including eg tunefs'ing N devices)
        SSH_READ_TIMEOUT = self.timeout

        user, hostname, port = self.ssh_params()

        args = {"username": user,
                "timeout": SOCKET_TIMEOUT}
        if port:
            args["port"] = int(port)
        # Note: paramiko has a hardcoded 15 second timeout on SSH handshake after
        # successful TCP connection (Transport.banner_timeout).
        ssh.connect(hostname, **args)
        transport = ssh.get_transport()
        transport.set_keepalive(20)
        channel = transport.open_session()
        channel.settimeout(SSH_READ_TIMEOUT)

        header = "====\nSSH %s\nCommand: '%s'\n====\n\n" % (self.address, command)
        self.console_append(header)

        channel.exec_command(command)

        stderr_buf = ""
        stdout_buf = ""
        while (not channel.exit_status_ready()) or channel.recv_ready() or channel.recv_stderr_ready():
            while channel.recv_ready():
                chunk = channel.recv(4096)
                stdout_buf += chunk
            while channel.recv_stderr_ready():
                chunk = channel.recv_stderr(4096)
                stderr_buf += chunk
                self.console_append(chunk)

            time.sleep(0.1)

        result_code = channel.recv_exit_status()

        ssh.close()

        self.log.debug("ssh:%s:%s:%s" % (self.address, result_code, command))
        if result_code != 0:
            self.log.error("ssh: nonzero rc %d" % result_code)
            self.log.error(stdout_buf)
            self.log.error(stderr_buf)
        return result_code, stdout_buf, stderr_buf

    def invoke(self, action, args = {}):
        args_str = " ".join(["--%s=\"%s\"" % (k, v) for (k, v) in args.items()])
        cmdline = "chroma-agent %s %s" % (action, args_str)
        self.log.debug("%s.invoke: %s" % (self.__class__.__name__, cmdline))
        code, out, err = self.ssh(cmdline)

        if code == 0:
            try:
                data = json.loads(out)
            except ValueError:
                raise AgentException(self.address, action, args, "Malformed JSON: %s" % out)

            try:
                if data['success']:
                    return data['result']
                else:
                    backtrace = data['backtrace']
                    self.log.error("Agent returned exception from host %s running '%s': %s" % (self.address, cmdline, backtrace))
                    raise AgentException(self.address, action, args, backtrace)
            except KeyError, e:
                raise AgentException(self.address, action, args, "Malformed output (%s) from agent: '%s'" % (e, out))

        else:
            raise AgentException(self.address, action, args, "Error %s running agent: %s" % (code, err))
