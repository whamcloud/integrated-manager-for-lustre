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
            q = conn.SimpleQueue(self.name, serializer = 'json',
                                 exchange_opts={'durable': False}, queue_opts={'durable': False})
            q.put(body)

    def purge(self):
        with _amqp_connection() as conn:
            purged = conn.SimpleQueue(self.name,
                                      exchange_opts={'durable': False}, queue_opts={'durable': False}).consumer.purge()
            log.info("Purged %s messages from '%s' queue" % (purged, self.name))

    def __init__(self):
        self._stopping = threading.Event()

    def stop(self):
        log.info("Stopping ServiceQueue %s" % self.name)
        self._stopping.set()

    def serve(self, callback):
        from Queue import Empty as QueueEmpty
        with _amqp_connection() as conn:
            q = conn.SimpleQueue(self.name, serializer = 'json',
                                 exchange_opts={'durable': False}, queue_opts={'durable': False})
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


class AgentRxQueue(ServiceQueue):
    def __route_message(self, message):
        if message['type'] == 'DATA' and self.__data_callback:
            self.__data_callback(message['fqdn'], message['body'])
        elif self.__session_callback:
            self.__session_callback(message)
        else:
            # Not a data message, and no session callback, drop.
            pass

    def __init__(self, plugin):
        """Specialization of ServiceQueue for receiving messages from agents:
            the callback invoked depends on the message_type.  Instead of
            setting the queue name, set the plugin name."""
        super(AgentRxQueue, self).__init__()
        self.name = "agent_%s_rx" % plugin

    def serve(self, data_callback = None, session_callback = None):
        """Data callback will receive only DATA mesages, being passed the fqdn and the body (i.e.
        the object returned by a device plugin).  Session callback will receive all messages,
        including the outer envelope.

        Simple consumer services should just set data_callback.  Session-aware services should
        set session_callback.
        """
        if data_callback is None and session_callback is None:
            raise AssertionError('Set at least one callback')

        self.__data_callback = data_callback
        self.__session_callback = session_callback

        return ServiceQueue.serve(self, self.__route_message)
