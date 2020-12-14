# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import Queue
from collections import defaultdict
import json
import socket
import threading
import traceback
import datetime
import sys
from chroma_agent.plugin_manager import (
    DevicePluginMessageCollection,
    DevicePluginMessage,
    PRIO_HIGH,
)
import requests
from chroma_agent import version
from chroma_agent.log import daemon_log, console_log, logging_in_debug_mode
from iml_common.lib.date_time import IMLDateTime
from iml_common.lib.util import ExceptionThrowingThread

MAX_BYTES_PER_POST = 8 * 1024 ** 2  # 8MiB, should be <= SSLRenegBufferSize

MIN_SESSION_BACKOFF = datetime.timedelta(seconds=10)
MAX_SESSION_BACKOFF = datetime.timedelta(seconds=60)

GET_REQUEST_TIMEOUT = 60.0
POST_REQUEST_TIMEOUT = 60.0

# FIXME: this file needs a concurrency review pass


class CryptoClient(object):
    def __init__(self, url, crypto, fqdn=None):
        self.url = url
        self._crypto = crypto
        self.fqdn = fqdn
        if not self.fqdn:
            self.fqdn = socket.getfqdn()

    def get(self, **kwargs):
        kwargs["timeout"] = GET_REQUEST_TIMEOUT
        return self.request("get", **kwargs)

    def post(self, data, **kwargs):
        kwargs["timeout"] = POST_REQUEST_TIMEOUT
        return self.request("post", data=json.dumps(data), **kwargs)

    def request(self, method, **kwargs):
        cert, key = self._crypto.certificate_file, self._crypto.private_key_file
        if cert:
            kwargs["cert"] = (cert, key)

        try:
            response = requests.request(
                method,
                self.url,
                # FIXME: set verify to true if we have a CA bundle
                verify=False,
                headers={"Content-Type": "application/json"},
                **kwargs
            )
        except (
            socket.error,
            requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout,
            requests.exceptions.SSLError,
        ) as e:
            daemon_log.error("Error connecting to %s: %s" % (self.url, e))
            raise HttpError()
        except Exception as e:
            # If debugging is enabled meaning we are in test for example then raise the error again and the app
            # will crash. If debugging not enabled then this is a user scenario and it is better that we attempt
            # to carry on. No data will be transferred and so badness cannot happen.
            daemon_log.error("requests returned an unexpected error %s" % e)

            if logging_in_debug_mode:
                raise

            raise HttpError()

        if not response.ok:
            daemon_log.error("Bad status %s from %s to %s" % (response.status_code, method, self.url))
            if response.status_code == 413:
                daemon_log.error("Oversized request: %s" % json.dumps(kwargs, indent=2))
            raise HttpError()
        try:
            return response.json()
        except ValueError:
            return None


class AgentDaemonContext(object):
    """
    Simple class that may be expanded in the future to allow more AgentDaemon context to be passed to action_plugins
    (and potentially others)
    """

    def __init__(self, plugin_sessions):
        """
        :param plugin_sessions: A dictionary of plugin sessions, the key is the name of the plugin 'linux' for example.
        """
        self.plugin_sessions = plugin_sessions


class AgentClient(CryptoClient):
    def __init__(self, url, action_plugins, device_plugins, server_properties, crypto):
        super(AgentClient, self).__init__(url, crypto)

        self._fqdn = server_properties.fqdn
        self._nodename = server_properties.nodename

        self.boot_time = server_properties.boot_time
        self.start_time = IMLDateTime.utcnow()

        self.action_plugins = action_plugins
        self.device_plugins = device_plugins
        self.writer = HttpWriter(self)
        self.reader = HttpReader(self)
        self.sessions = SessionTable(self)

        self.stopped = threading.Event()

    def start(self):
        self.reader.start()
        self.writer.start()

    def stop(self):
        daemon_log.debug("Client stopping...")
        self.reader.stop()
        self.writer.stop()
        self.stopped.set()

    def join(self):
        daemon_log.debug("Client joining...")
        # self.reader.join()
        self.writer.join()
        self.sessions.terminate_all()
        daemon_log.debug("Client joined")

    def register(self, address=None):
        # FIXME: At this time the 'capabilities' attribute is unused on the manager
        data = {
            "address": address,
            "fqdn": self._fqdn,
            "nodename": self._nodename,
            "capabilities": self.action_plugins.capabilities,
            "version": version(),
            "csr": self._crypto.generate_csr(self._fqdn),
        }

        if self._fqdn == "localhost.localdomain":
            console_log.error("Registration failed, FQDN is localhost.localdomain")
            raise RuntimeError("Name resolution error, FQDN resolves to localhost.localdomain")

        # TODO: during registration, we should already have the authority certificate
        # so we should establish an HTTPS connection (no client cert) with the
        # manager, and verify that the manager's certificate is signed and for
        # an address matching self.url

        try:
            result = self.post(data)
        except HttpError:
            console_log.error("Registration failed to %s with request %s" % (self.url, data))
            raise
        else:
            return result


MESSAGE_TYPES = [
    "SESSION_CREATE_REQUEST",
    "SESSION_CREATE_RESPONSE",
    "SESSION_TERMINATE",
    "DATA",
    "SESSION_TERMINATE_ALL",
]


class Message(object):
    def __cmp__(self, other):
        # If this message has a body, use its priority.  Otherwise it is a
        # control plane message, set its priority to high.
        prio_self = self.body.priority if self.body is not None else PRIO_HIGH
        prio_other = other.body.priority if other.body is not None else PRIO_HIGH
        return cmp(prio_self, prio_other)

    def __init__(
        self,
        type=None,
        plugin_name=None,
        body=None,
        session_id=None,
        session_seq=None,
        callback=None,
    ):
        if type is not None:
            assert type in MESSAGE_TYPES
            self.type = type
            self.plugin_name = plugin_name
            self.body = body
            self.session_id = session_id
            self.session_seq = session_seq
            self.callback = callback

    def parse(self, data):
        assert data["type"] in MESSAGE_TYPES
        self.type = data["type"]
        self.plugin_name = data["plugin"]
        self.body = data["body"]
        self.session_id = data["session_id"]
        self.session_seq = data["session_seq"]

    def dump(self, fqdn):
        if isinstance(self.body, DevicePluginMessage):
            body = self.body.message
        else:
            body = self.body

        return {
            "type": self.type,
            "plugin": self.plugin_name,
            "session_id": self.session_id,
            "session_seq": self.session_seq,
            "body": body,
            "fqdn": fqdn,
        }


class Session(object):
    POLL_PERIOD = 10

    def __init__(self, client, id, plugin_name):
        self.id = id
        self._plugin_name = plugin_name
        self._plugin = client.device_plugins.get(plugin_name)(self)
        self._writer = client.writer
        self._client = client
        self._poll_counter = 0
        self._seq = 0
        self._last_poll = None

    def poll(self):
        now = datetime.datetime.now()
        if self._last_poll is None or now - self._last_poll > datetime.timedelta(seconds=self.POLL_PERIOD):
            self._last_poll = now
            try:
                self._poll_counter += 1
                if self._poll_counter == 1:
                    return self._plugin.start_session()
                else:
                    return self._plugin.update_session()
            except NotImplementedError:
                return None

    def send_message(self, body, callback=None):
        daemon_log.info("Session.send_message %s/%s" % (self._plugin_name, self.id))
        self._writer.put(Message("DATA", self._plugin_name, body, self.id, self._seq, callback=callback))
        self._seq += 1

    def receive_message(self, body):
        daemon_log.info("Session.receive_message %s/%s" % (self._plugin_name, self.id))
        self._plugin.on_message(body)

    def teardown(self):
        self._plugin.teardown()


class SessionTable(object):
    """Collection of sessions for each DevicePlugin, updated by HttpControl"""

    def __init__(self, client):
        # Map of plugin name to session object
        self._sessions = {}
        self._client = client

        # Map of plugin name to when we last requested a session
        self._requested_at = {}
        # Map of plugin name to how long to wait between session requests
        self._backoffs = defaultdict(lambda: MIN_SESSION_BACKOFF)

    def create(self, plugin_name, id):
        daemon_log.info("SessionTable.create %s/%s" % (plugin_name, id))
        self._requested_at.pop(plugin_name, None)
        self._backoffs.pop(plugin_name, None)
        self._sessions[plugin_name] = Session(self._client, id, plugin_name)

    def get(self, plugin_name, id=None):
        session = self._sessions[plugin_name]
        if id is not None and session.id != id:
            raise KeyError()
        return session

    def terminate(self, plugin_name):
        try:
            session = self.get(plugin_name)
        except KeyError:
            daemon_log.warning("SessionTable.terminate not found %s" % plugin_name)
            return
        else:
            daemon_log.info("SessionTable.terminate %s/%s" % (plugin_name, session.id))
            session.teardown()
            try:
                del self._sessions[plugin_name]
            except KeyError:
                daemon_log.warning("SessionTable.terminate session object already gone")

    def terminate_all(self):
        for session in self._sessions.values():
            session.teardown()
        self._sessions.clear()


class ExceptionCatchingThread(threading.Thread):
    def run(self):
        try:
            self._run()
        except Exception:
            backtrace = "\n".join(traceback.format_exception(*(sys.exc_info())))
            daemon_log.error("Unhandled error in thread %s: %s" % (self.__class__.__name__, backtrace))
            sys.exit(-1)


class HttpWriter(ExceptionCatchingThread):
    """Send messages to the manager, and handle control messages received in response"""

    def __init__(self, client):
        super(HttpWriter, self).__init__()
        self._client = client
        self._stopping = threading.Event()
        self._messages_waiting = threading.Event()
        self._last_poll = defaultdict(lambda: None)
        self._messages = Queue.PriorityQueue()
        self._retry_messages = Queue.Queue()

    def put(self, message):
        """Called from a different thread context than the main loop"""
        self._messages.put(message)
        self._messages_waiting.set()

    def _run_plugin(self, plugin_name):
        # Ensure that there is a time at least this long between
        # calls to .poll() (just to avoid spinning)
        POLL_PERIOD = 1.0

        while not self._stopping.is_set():
            started_at = datetime.datetime.now()

            self.poll(plugin_name)

            # Ensure that we poll at most every POLL_PERIOD
            self._stopping.wait(timeout=max(0, POLL_PERIOD - (datetime.datetime.now() - started_at).seconds))

    def _run(self):
        threads = []

        for plugin_name in self._client.device_plugins.get_plugins():
            thread = ExceptionThrowingThread(target=self._run_plugin, args=(plugin_name,))
            threads.append(thread)
            thread.start()

        while not self._stopping.is_set():
            while not (self._messages.empty() and self._retry_messages.empty()):
                self.send()

            self._messages_waiting.wait()
            self._messages_waiting.clear()

        ExceptionThrowingThread.wait_for_threads(threads)

    def stop(self):
        self._stopping.set()
        self._messages_waiting.set()  # Trigger this to cause  _run to loop spin and see that _stopping is set.

    def send(self):
        """Return True if the POST succeeds, else False"""
        messages = []
        completion_callbacks = []

        post_envelope = {
            "messages": [],
            "server_boot_time": self._client.boot_time.isoformat() + "Z",
            "client_start_time": self._client.start_time.isoformat() + "Z",
        }

        # Any message we drop will need its session killed
        kill_sessions = set()

        messages_bytes = len(json.dumps(post_envelope))
        while True:
            try:
                message = self._retry_messages.get_nowait()
                daemon_log.debug("HttpWriter got message from retry queue")
            except Queue.Empty:
                try:
                    message = self._messages.get_nowait()
                    daemon_log.debug("HttpWriter got message from primary queue")
                except Queue.Empty:
                    break

            if message.callback:
                completion_callbacks.append(message.callback)
            message_length = len(json.dumps(message.dump(self._client._fqdn)))

            if message_length > MAX_BYTES_PER_POST:
                daemon_log.warning(
                    "Oversized message %s/%s: %s"
                    % (
                        message_length,
                        MAX_BYTES_PER_POST,
                        message.dump(self._client._fqdn),
                    )
                )

            if messages and message_length > MAX_BYTES_PER_POST - messages_bytes:
                # This message will not fit into this POST: pop it back into the queue
                daemon_log.info(
                    "HttpWriter message %s overflowed POST %s/%s (%d "
                    "messages), enqueuing"
                    % (
                        message.dump(self._client._fqdn),
                        message_length,
                        MAX_BYTES_PER_POST,
                        len(messages),
                    )
                )
                self._retry_messages.put(message)
                break

            messages.append(message)
            messages_bytes += message_length

        daemon_log.debug("HttpWriter sending %s messages" % len(messages))
        try:
            post_envelope["messages"] = [m.dump(self._client._fqdn) for m in messages]
            self._client.post(post_envelope)
        except HttpError:
            daemon_log.warning("HttpWriter: request failed")
            # Terminate any sessions which we've just droppped messages for
            for message in messages:
                if message.type == "DATA":
                    kill_sessions.add(message.plugin_name)
            for plugin_name in kill_sessions:
                self._client.sessions.terminate(plugin_name)

            return False
        else:
            return True
        finally:
            for callback in completion_callbacks:
                callback()

    def poll(self, plugin_name):
        """
        For any plugins that don't have a session, try asking for one.
        For any ongoing sessions, invoke the poll callback
        """

        now = datetime.datetime.now()

        try:
            session = self._client.sessions.get(plugin_name)
        except KeyError:
            # Request to open a session
            #
            if plugin_name in self._client.sessions._requested_at:
                next_request_at = (
                    self._client.sessions._requested_at[plugin_name] + self._client.sessions._backoffs[plugin_name]
                )
                if now < next_request_at:
                    # We're still in our backoff period, skip requesting a session
                    daemon_log.debug("Delaying session request until %s" % next_request_at)
                    return
                else:
                    if self._client.sessions._backoffs[plugin_name] < MAX_SESSION_BACKOFF:
                        self._client.sessions._backoffs[plugin_name] *= 2

            daemon_log.debug("Requesting session for plugin %s" % plugin_name)
            self._client.sessions._requested_at[plugin_name] = now
            self.put(Message("SESSION_CREATE_REQUEST", plugin_name))
        else:
            try:
                data = session.poll()
            except Exception:
                backtrace = "\n".join(traceback.format_exception(*(sys.exc_info())))
                daemon_log.error("Error in plugin %s: %s" % (plugin_name, backtrace))
                self._client.sessions.terminate(plugin_name)
                self.put(Message("SESSION_CREATE_REQUEST", plugin_name))
            else:
                if data is not None:
                    if isinstance(data, DevicePluginMessageCollection):
                        for message in data:
                            session.send_message(DevicePluginMessage(message, priority=data.priority))
                    elif isinstance(data, DevicePluginMessage):
                        session.send_message(data)
                    else:
                        session.send_message(DevicePluginMessage(data))


class HttpReader(ExceptionCatchingThread):
    """Receive data messages from the manager"""

    # Time to wait after a failed HTTP request
    HTTP_RETRY_PERIOD = 10

    def __init__(self, client):
        super(HttpReader, self).__init__()

        # Clean timely teardown isn't possible because of blocking IO in HTTP long poll
        self.daemon = True
        self._client = client
        self._stopping = threading.Event()

    def _handle_messages(self, messages):
        daemon_log.info("HttpReader: got %s messages" % (len(messages)))
        for message in messages:
            m = Message()
            m.parse(message)
            daemon_log.info("HttpReader: %s(%s, %s)" % (m.type, m.plugin_name, m.session_id))

            try:
                if m.type == "SESSION_CREATE_RESPONSE":
                    self._client.sessions.create(m.plugin_name, m.session_id)
                elif m.type == "SESSION_TERMINATE_ALL":
                    self._client.sessions.terminate_all()
                elif m.type == "SESSION_TERMINATE":
                    self._client.sessions.terminate(m.plugin_name)
                elif m.type == "DATA":
                    try:
                        session = self._client.sessions.get(m.plugin_name, m.session_id)
                    except KeyError:
                        daemon_log.warning(
                            "Received a message for unknown session %s/%s" % (m.plugin_name, m.session_id)
                        )
                    else:
                        # We have successfully routed the message to the plugin instance
                        # for this session
                        try:
                            session.receive_message(m.body)
                        except:
                            daemon_log.error(
                                "%s/%s raised an exception: %s" % (m.plugin_name, m.session_id, traceback.format_exc())
                            )
                            self._client.sessions.terminate(m.plugin_name)
                else:
                    raise NotImplementedError(m.type)
            except Exception:
                backtrace = "\n".join(traceback.format_exception(*(sys.exc_info())))
                daemon_log.error("Plugin exception handling data message: %s" % backtrace)

    def _run(self):
        get_args = {
            "server_boot_time": self._client.boot_time.isoformat() + "Z",
            "client_start_time": self._client.start_time.isoformat() + "Z",
        }
        while not self._stopping.is_set():
            daemon_log.info("HttpReader: get")
            try:
                body = self._client.get(params=get_args)
            except HttpError:
                daemon_log.warning("HttpReader: request failed")
                # We potentially dropped TX messages if this happened, which could include
                # session control messages, so have to completely reset.
                # NB could change this to only terminate_all if an HTTP request was started: there is
                # no need to do the teardown if we didn't even get a TCP connection to the manager.
                self._client.sessions.terminate_all()

                self._stopping.wait(timeout=self.HTTP_RETRY_PERIOD)
                continue
            else:
                self._handle_messages(body["messages"])
        daemon_log.info("HttpReader: stopping")

    def stop(self):
        self._stopping.set()


#
#    def join(self, *args, **kwargs):
#        # Clean timely teardown isn't possible because of blocking IO in HTTP long poll,
#        # so this thread is run with daemon=True
#        pass


class HttpError(Exception):
    pass
