#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import Queue
from collections import defaultdict
import json
import socket
import threading
import traceback
import datetime
import sys
import requests
from chroma_agent import version
from chroma_agent.log import daemon_log, console_log


# FIXME: this file needs a concurrency review pass


class AgentClient(object):
    def __init__(self, url, action_plugins, device_plugins, server_properties, crypto):

        self._fqdn = server_properties.fqdn
        self._nodename = server_properties.nodename
        self._crypto = crypto

        self.boot_time = server_properties.boot_time
        self.start_time = datetime.datetime.utcnow()

        self.url = url
        self.action_plugins = action_plugins
        self.device_plugins = device_plugins
        self.writer = HttpWriter(self)
        self.reader = HttpReader(self)
        self.sessions = SessionTable(self)

        self.stopped = threading.Event()

    def get(self, **kwargs):
        return self.request('get', **kwargs)

    def post(self, data, **kwargs):
        return self.request('post', data = json.dumps(data), **kwargs)

    def request(self, method, **kwargs):
        cert, key = self._crypto.certificate_file, self._crypto.private_key_file
        if cert:
            kwargs['cert'] = (cert, key)

        try:
            response = requests.request(method, self.url,
                # FIXME: set verify to true if we have a CA bundle
                verify = False,
                headers = {"Content-Type": "application/json"},
                **kwargs)
        except socket.error, e:
            daemon_log.error("Error conntecting to %s: %s" % (self.url, e))
            raise HttpError()

        if response.status_code / 100 != 2:
            daemon_log.error("Bad status %s from %s" % (response.status_code, self.url))
            raise HttpError()
        try:
            return response.json()
        except ValueError:
            return None

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
        #self.reader.join()
        self.writer.join()
        self.sessions.terminate_all()
        daemon_log.debug("Client joined")

    def register(self, address = None):
        data = {
            'address': address,
            'fqdn': self._fqdn,
            'nodename': self._nodename,
            'capabilities': self.action_plugins.capabilities,
            'version': version(),
            'csr': self._crypto.generate_csr(self._fqdn)
        }

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

MESSAGE_TYPES = ["SESSION_CREATE_REQUEST",
                 "SESSION_CREATE_RESPONSE",
                 "SESSION_TERMINATE",
                 "DATA",
                 "SESSION_TERMINATE_ALL"]


class Message(object):
    def __init__(self, type = None, plugin_name = None, body = None, session_id = None, session_seq = None):
        if type is not None:
            assert type in MESSAGE_TYPES
            self.type = type
            self.plugin_name = plugin_name
            self.body = body
            self.session_id = session_id
            self.session_seq = session_seq

    def parse(self, data):
        assert data['type'] in MESSAGE_TYPES
        self.type = data['type']
        self.plugin_name = data['plugin']
        self.body = data['body']
        self.session_id = data['session_id']
        self.session_seq = data['session_seq']

    def dump(self):
        return {
            'type': self.type,
            'plugin': self.plugin_name,
            'session_id': self.session_id,
            'session_seq': self.session_seq,
            'body': self.body
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
        if self._last_poll is None or now - self._last_poll > datetime.timedelta(seconds = self.POLL_PERIOD):
            self._last_poll = now
            try:
                self._poll_counter += 1
                if self._poll_counter == 1:
                    return self._plugin.start_session()
                else:
                    return self._plugin.update_session()
            except NotImplementedError:
                return None

    def send_message(self, body):
        daemon_log.info("Session.send_message %s/%s" % (self._plugin_name, self.id))
        self._writer.put(Message("DATA", self._plugin_name, body, self.id, self._seq))
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

    def create(self, plugin_name, id):
        daemon_log.info("SessionTable.create %s/%s" % (plugin_name, id))
        self._sessions[plugin_name] = Session(self._client, id, plugin_name)

    def get(self, plugin_name, id = None):
        session = self._sessions[plugin_name]
        if id is not None and session.id != id:
            raise KeyError()
        return session

    def terminate(self, plugin_name, id):
        try:
            session = self.get(plugin_name, id)
        except KeyError:
            daemon_log.warning("SessionTable.terminate not found %s/%s" % (plugin_name, id))
            return
        else:
            daemon_log.info("SessionTable.terminate %s/%s" % (plugin_name, id))
            session.teardown()
            del self._sessions[plugin_name]

    def terminate_all(self):
        for session in self._sessions.values():
            session.teardown()
        self._sessions.clear()


class ExceptionCatchingThread(threading.Thread):
    def run(self):
        try:
            self._run()
        except Exception:
            backtrace = '\n'.join(traceback.format_exception(*(sys.exc_info())))
            daemon_log.error("Unhandled error in thread %s: %s" % (self.__class__.__name__, backtrace))
            sys.exit(-1)


class HttpWriter(ExceptionCatchingThread):
    """Send messages to the manager, and handle control messages received in response"""

    # Interval with which plugins are polled for update messages
    POLL_INTERVAL = datetime.timedelta(seconds = 10)

    def __init__(self, client):
        super(HttpWriter, self).__init__()
        self._client = client
        self._stopping = threading.Event()
        self._last_poll = defaultdict(lambda: None)
        self._messages = Queue.Queue()

    def put(self, message):
        """Called from a different thread context than the main loop"""
        self._messages.put(message)

    def _run(self):
        while not self._stopping.is_set():
            # FIXME: this isn't terribly efficient (waking up every second), because on the one hand
            # we usually want a delay of at least 10 seconds between polls (so
            # we should sleep), but on the other hand, when a session is established
            # we want to get its first message nice and promptly.

            self.poll()

            while not self._messages.empty():
                self.send()

            if self._messages.empty():
                self._stopping.wait(timeout = 1)

    def stop(self):
        self._stopping.set()

    def send(self):
        messages = []
        while True:
            try:
                messages.append(self._messages.get_nowait())
            except Queue.Empty:
                break

        try:
            self._client.post({'messages': [m.dump() for m in messages]})
        except HttpError:
            # Terminate any sessions which we've just lost messages for
            # FIXME: up to a point, we should keep these messages around
            # and try retransmitting them, to avoid a single failed POST
            # resetting all the sessions.
            kill_sessions = set()
            for message in messages:
                if message.type == 'DATA':
                    kill_sessions.add((message.plugin_name, message.session_id))
            for plugin_name, session_id in kill_sessions:
                self._client.sessions.terminate(plugin_name, session_id)

    def poll(self):
        """
        For any plugins that don't have a session, try asking for one.
        For any ongoing sessions, invoke the poll callback
        """

        for plugin_name, plugin_klass in self._client.device_plugins.get_plugins().items():
            try:
                session = self._client.sessions.get(plugin_name)
            except KeyError:
                # Request to open a session
                # FIXME: don't do this so frequently when we're not getting
                # successful session creations (either because our requests
                # aren't getting through or because the session setup is failing)
                daemon_log.debug("Requesting session for plugin %s" % plugin_name)
                self._messages.put(Message("SESSION_CREATE_REQUEST", plugin_name))
            else:
                try:
                    data = session.poll()
                except Exception:
                    backtrace = '\n'.join(traceback.format_exception(*(sys.exc_info())))
                    daemon_log.error("Error in plugin %s: %s" % (plugin_name, backtrace))
                    self._client.sessions.terminate(plugin_name, session.id)
                    self._messages.put(Message("SESSION_CREATE_REQUEST", plugin_name))
                else:
                    if data is not None:
                        session.send_message(data)


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
                    self._client.sessions.terminate(m.plugin_name, m.session_id)
                elif m.type == "DATA":
                    try:
                        session = self._client.sessions.get(m.plugin_name, m.session_id)
                    except KeyError:
                        daemon_log.warning("Received a message for unknown session %s/%s" % (m.plugin_name, m.session_id))
                    else:
                        # We have successfully routed the message to the plugin instance
                        # for this session
                        session.receive_message(m.body)
                        # TODO: if a plugin throws an exception, kill its session (buggy plugin!)
                else:
                    raise NotImplementedError(m.type)
            except Exception:
                backtrace = '\n'.join(traceback.format_exception(*(sys.exc_info())))
                daemon_log.error("Plugin exception handling data message: %s" % backtrace)

    def _run(self):
        get_args = {
            'server_boot_time': self._client.boot_time.isoformat() + "Z",
            'client_start_time': self._client.start_time.isoformat() + "Z"
        }
        while not self._stopping.is_set():
            daemon_log.info("HttpReader: get")
            try:
                body = self._client.get(params = get_args)
            except HttpError:
                daemon_log.warning("HttpReader: request failed")
                self._stopping.wait(timeout = self.HTTP_RETRY_PERIOD)
                continue
            else:
                self._handle_messages(body['messages'])
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
