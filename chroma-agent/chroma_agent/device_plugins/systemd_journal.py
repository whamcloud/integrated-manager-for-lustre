# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import Queue
import threading
from chroma_agent.log import console_log
from chroma_agent.plugin_manager import DevicePlugin, DevicePluginMessageCollection, PRIO_LOW

import datetime
import pytz
from tzlocal import get_localzone
import systemd.journal

# FIXME: shonky scope of this, it should be part of SYslogdeviceplugin and get set up and torn down appropriately
_queue = Queue.Queue()


MAX_LOG_LINES_PER_MESSAGE = 64


def parse_journal(data):
    """"
    Parse systemd journal entries.

    We do this on the agent rather than the manager because:
     * It allows us to distribute this bit of load
     * It localizes the means of log acquisition entirely to the agent,
       the manager never has any idea that the journal is in use or what
       forwarding protocol is being used.
    """

    utc_dt = get_localzone().localize(data['__REALTIME_TIMESTAMP'], is_dst=None).astimezone(pytz.utc)

    return {
        'datetime': datetime.datetime.isoformat(utc_dt),
        'severity': data['PRIORITY'],
        'facility': data.get('SYSLOG_FACILITY', 3),
        'source': data.get('SYSLOG_IDENTIFIER', 'unknown'),
        'message': data['MESSAGE']
    }


class SystemdJournalListener(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(SystemdJournalListener, self).__init__(*args, **kwargs)
        self.should_run = True

    def run(self):
        j = systemd.journal.Reader()
        j.seek_tail()
        while self.should_run:
            if j.wait(1) == systemd.journal.APPEND:
                for entry in j:
                     _queue.put(parse_journal(entry))

    def stop(self):
        console_log.debug("SystemdJournalListener.stop")
        self.should_run = False


class SystemdJournalDevicePlugin(DevicePlugin):
    def __init__(self, *args, **kwargs):
        super(SystemdJournalDevicePlugin, self).__init__(*args, **kwargs)
        self._listener = SystemdJournalListener()
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
                total_lines += len(lines)
                messages.append({'log_lines': lines})
            else:
                break

        console_log.debug("SystemdJournalDevicePlugin: %s lines in %s messages" % (total_lines, len(messages)))

        if messages:
            return messages
        else:
            return None

    def teardown(self):
        console_log.debug("SystemdJournalDevicePlugin.teardown")
        self._listener.stop()
        self._listener.join()
