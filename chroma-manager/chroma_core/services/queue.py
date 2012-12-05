#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


"""Chroma services may subscribe to named queues using this module.  The `ServiceQueue` class is a wrapper
around an AMQP queue."""
import threading

from chroma_core.services import _amqp_connection
from chroma_core.services.log import log_register


log = log_register('queue')


class ServiceQueue(object):
    """Simple FIFO queue, multiple senders, single receiver.  Payloads
    must be JSON-serializable.

    Subclass this for each named queue, setting the `name` class attribute.

    Example declaring a queue:
    ::

        class AcmeQueue(ServiceQueue):
            name = 'acme'

    Example sending to a queue:
    ::

        AcmeQueue().put({'foo': 'bar'})

    """
    name = None

    def put(self, body):
        with _amqp_connection() as conn:
            q = conn.SimpleQueue(self.name, serializer = 'json')
            q.put(body)

    def purge(self):
        with _amqp_connection() as conn:
            purged = conn.SimpleQueue(self.name).consumer.purge()
            log.info("Purged %s messages from '%s' queue" % (purged, self.name))

    def __init__(self):
        self._stopping = threading.Event()

    def stop(self):
        self._stopping.set()

    def serve(self, callback):
        from Queue import Empty as QueueEmpty
        with _amqp_connection() as conn:
            q = conn.SimpleQueue(self.name, serializer = 'json')
            # FIXME: it would be preferable to avoid waking up so often: really what is wanted
            # here is to sleep on messages or a stop event.
            while not self._stopping.is_set():
                try:
                    message = q.get(timeout = 1)
                    message.ack()
                    message = message.decode()
                    callback(message)
                except QueueEmpty:
                    pass
