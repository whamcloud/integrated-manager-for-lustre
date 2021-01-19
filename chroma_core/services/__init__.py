# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


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

    @property
    def name(self):
        return self.__class__.__module__.split(".")[-1]

    def run(self):
        pass

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
        self.log = log_register("service_thread")
        self._started = False

    def start(self):
        super(ServiceThread, self).start()
        self._started = True

    def run(self):
        if hasattr(self.service, "name"):
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
            backtrace = "\n".join(traceback.format_exception(*(exc_info or sys.exc_info())))
            self.log.error("Exception in main loop.  backtrace: %s" % backtrace)
            os._exit(-1)

    def stop(self):
        if not self._started:
            self.log.error(
                "Attempted to stop ServiceThread '%s' before it was started." % self.service.__class__.__name__
            )
            os._exit(-1)
        else:
            self.service.stop()


def _amqp_connection():
    return BrokerConnection(settings.BROKER_URL)


def _amqp_exchange():
    return Exchange("rpc", type="topic", delivery_mode=TRANSIENT_DELIVERY_MODE, durable=False)
