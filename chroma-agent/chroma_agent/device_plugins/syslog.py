# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import Queue
import SocketServer
import threading
import signal
from chroma_agent.log import console_log
from chroma_agent.plugin_manager import DevicePlugin, DevicePluginMessageCollection, PRIO_LOW

import os

# FIXME: shonky scope of this, it should be part of SYslogdeviceplugin and get set up and torn down appropriately
_queue = Queue.Queue()


# Deliberately using a non-default port so that we can run on the same
# host as a syslog daemon which is listening (not how we configure it, but
# let's not make assumptions).
SYSLOG_PORT = 515

MAX_LOG_LINES_PER_MESSAGE = 64


def parse_rsyslog(data):
    """"
    Parse RSYSLOG_ForwardFormat.

    We do this on the agent rather than the manager because:
     * It allows us to distribute this bit of load
     * It localizes the means of log acquisition entirely to the agent,
       the manager never has any idea that rsyslog is in use or what
       forwarding protocol is being used.
    """

    prio_date, hostname, source, msg = data.split(" ", 3)
    source = source[:-1]
    msg = msg.strip()
    close_angle = prio_date.find(">")
    priority = int(prio_date[1:close_angle], 10)
    datetime_iso8601 = prio_date[close_angle + 1:]

    facility = priority >> 3
    severity = priority - facility

    return {
        'datetime': datetime_iso8601,
        'severity': severity,
        'facility': facility,
        'source': source,
        'message': msg
    }


class SyslogHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        data = self.rfile.readline().strip()

        _queue.put(parse_rsyslog(data))


class SyslogListener(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(SyslogListener, self).__init__(*args, **kwargs)
        self.server = SocketServer.TCPServer(("127.0.0.1", SYSLOG_PORT), SyslogHandler, bind_and_activate = False)
        self.server.allow_reuse_address = True

    def run(self):
        self.server.serve_forever()

    def bind(self):
        # FIXME: handle the case where rsyslog isn't running (warn)
        # and consider how we might cleanly deal with installing
        # on rsyslog-less systems (which might nevertheless send us messages,
        # while violating our assumptions about the PID file location and
        # the meaning of HUP)

        os.kill(int(open('/var/run/syslogd.pid').read().strip()), signal.SIGHUP)

        self.server.server_bind()
        self.server.server_activate()

    def stop(self):
        console_log.debug("SyslogListener.stop")
        if self.server:
            console_log.debug("SyslogListener.stop: closing socket")
            self.server.shutdown()
            self.server.server_close()


class SyslogDevicePlugin(DevicePlugin):
    def __init__(self, *args, **kwargs):
        super(SyslogDevicePlugin, self).__init__(*args, **kwargs)
        self._listener = SyslogListener()
        # Call bind outside of the thread's run() so that if it fails we
        # can throw an exception here rather than having to communicate
        # with the thread.
        self._listener.bind()
        self._listener.start()

    def poll(self):
        result = []
        while True and len(result) < MAX_LOG_LINES_PER_MESSAGE:
            try:
                result.append(_queue.get_nowait())
            except Queue.Empty:
                break

        return result

    def start_session(self):
        return self.update_session()

    def update_session(self):
        messages = DevicePluginMessageCollection([], priority = PRIO_LOW)
        total_lines = 0
        while True:
            lines = self.poll()
            if lines:
                messages.append({'log_lines': lines})
            else:
                break

        console_log.debug("SyslogDevicePlugin: %lines in %s messages" % (total_lines, len(messages)))

        if messages:
            return messages
        else:
            return None

    def teardown(self):
        console_log.debug("SyslogDevicePlugin.teardown")
        self._listener.stop()
        self._listener.join()
