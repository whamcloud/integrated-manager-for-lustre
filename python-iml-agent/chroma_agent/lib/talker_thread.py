# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
talker thread class
"""

import threading

from chroma_agent.lib import networking


class TalkerThread(threading.Thread):
    """To reduce races and improve the chances of ring1 detection, we start
    a multicast "talker" thread which just sprays its multicast port
    at the multicast group. The idea is to fill in the "dead air" until
    one of the peers starts corosync.
    """

    def __init__(self, interface, log):
        super(TalkerThread, self).__init__()
        self._stop = threading.Event()
        self.interface = interface
        self.log = log
        self.daemon = True

    def stop(self):
        self._stop.set()
        self.join()
        self.log.debug("Talker thread stopped")

    def run(self):
        self.log.debug("Talker thread running")

        sock = networking.subscribe_multicast(self.interface)

        while not self._stop.is_set():
            sock.sendto(
                "%d\n\0" % self.interface.mcastport,
                (self.interface.mcastaddr, self.interface.mcastport),
            )
            self._stop.wait(0.25)
