#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import threading
import os

from kombu.connection import BrokerConnection
from kombu.messaging import Exchange
from chroma_core.services.log import log_register

import settings


class ChromaService(object):
    """Define a subclass of this for each service.  Must implement `start` and `stop`
    methods: typically starting a server/thread in `start` and tearing it down in `stop`.

    Use the `log` instance attribute for all logging, this is set up with a logger that
    tags messages with the service name.

    """
    def start(self):
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

    def run(self):
        try:
            self.service.run()
        except Exception:
            import sys
            import traceback
            exc_info = sys.exc_info()
            backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
            self.log.warning("Exception in main loop.  backtrace: %s" % backtrace)
            os._exit(-1)

    def stop(self):
        self.service.stop()


def _amqp_connection():
    return BrokerConnection("amqp://%s:%s@%s:%s/%s" % (
        settings.BROKER_USER,
        settings.BROKER_PASSWORD,
        settings.BROKER_HOST,
        settings.BROKER_PORT,
        settings.BROKER_VHOST))


def _amqp_exchange():
    return Exchange("rpc", type="topic", delivery_mode = 1)
