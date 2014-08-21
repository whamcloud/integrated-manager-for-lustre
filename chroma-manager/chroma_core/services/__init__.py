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


import threading
from kombu.connection import BrokerConnection
from kombu.messaging import Exchange
from kombu.entity import TRANSIENT_DELIVERY_MODE
import os
import sys
import traceback

from chroma_core.services.log import log_register, trace

import settings


class ChromaService(object):
    """Define a subclass of this for each service.  Must implement `start` and `stop`
    methods: typically starting a server/thread in `start` and tearing it down in `stop`.

    Use the `log` instance attribute for all logging, this is set up with a logger that
    tags messages with the service name.

    """

    def __init__(self):
        self.log = None
        # Enable long polling.
        from chroma_core.lib.long_polling import enable_long_polling
        assert enable_long_polling    # Prevent pep8 warning

    @property
    def name(self):
        return self.__class__.__module__.split('.')[-1]

    def run(self):
        raise NotImplementedError()

    def stop(self):
        pass


class ServiceThread(threading.Thread):
    """Sometimes a single service may have multiple threads of execution.  Use this
    class rather than the bare threading.Thread to help Chroma keep track of your threads.

    This wraps a Thread-like object which has a `run` and `stop` method, passed in at
    construction time`

    """

    def __init__(self, service):
        super(ServiceThread, self).__init__()
        self.service = service
        self.log = log_register('service_thread')
        self._started = False

    def start(self):
        super(ServiceThread, self).start()
        self._started = True

    def run(self):
        if hasattr(self.service, 'name'):
            name = self.service.name
        else:
            name = self.service.__class__.__name__
        self.log.debug("running ServiceThread '%s'" % name)
        self.name = name

        if trace:
            sys.settrace(trace)

        try:
            self.service.run()
        except Exception:
            exc_info = sys.exc_info()
            backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
            self.log.error("Exception in main loop.  backtrace: %s" % backtrace)
            os._exit(-1)

    def stop(self):
        if not self._started:
            self.log.error("Attempted to stop ServiceThread '%s' before it was started." % self.service.__class__.__name__)
            os._exit(-1)
        else:
            self.service.stop()


def _amqp_connection():
    return BrokerConnection(settings.BROKER_URL)


def _amqp_exchange():
    return Exchange("rpc", type="topic", delivery_mode=TRANSIENT_DELIVERY_MODE, durable=False)
