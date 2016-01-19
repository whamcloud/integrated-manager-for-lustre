#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


"""
talker thread class
"""

import threading

from chroma_agent.lib import networking


class TalkerThread(threading.Thread):
    """ To reduce races and improve the chances of ring1 detection, we start
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
            sock.sendto("%d\n\0" % self.interface.mcastport,
                        (self.interface.mcastaddr, self.interface.mcastport))
            self._stop.wait(0.25)
