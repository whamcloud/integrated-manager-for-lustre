#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


import Queue
import threading
from chroma_core.services import _amqp_connection, log_register
from chroma_core.services.queue import ServiceQueue


class AgentTxQueue(ServiceQueue):
    name = "agent_tx"


log = log_register(__name__)


class HostQueueCollection(object):
    def __init__(self):
        self._host_queues = {}

        # A queue for all plugin RX messages, will be fanned
        # out to an AMQP queue per plugin
        self.plugin_rx_queue = Queue.Queue()

        self._lock = threading.Lock()

    def get(self, fqdn):
        with self._lock:
            try:
                return self._host_queues[fqdn]
            except KeyError:
                queues = HostQueues(fqdn)
                self._host_queues[fqdn] = queues
                return queues

    def remove_host(self, fqdn):
        with self._lock:
            self._host_queues.pop(fqdn, None)

    def send(self, message):
        queues = self.get(message['fqdn'])
        queues.tx.put(message)

    def receive(self, message):
        self.plugin_rx_queue.put(message)


class HostQueues(object):
    """Both directions of messages for a single host"""
    def __init__(self, fqdn):
        self.fqdn = fqdn
        self.rx = Queue.Queue()
        self.tx = Queue.Queue()


class AmqpRxForwarder(object):
    def __init__(self, queue_collection):
        self._stopping = threading.Event()
        self._queue_collection = queue_collection

    def run(self):
        with _amqp_connection() as conn:
            while not self._stopping.is_set():
                try:
                    msg = self._queue_collection.plugin_rx_queue.get(block = True, timeout = 1)
                except Queue.Empty:
                    pass
                else:
                    plugin_name = msg['plugin']
                    rx_queue_name = "agent_%s_rx" % plugin_name
                    q = conn.SimpleQueue(rx_queue_name, serializer = 'json')
                    q.put(msg)

    def stop(self):
        self._stopping.set()


class AmqpTxForwarder(object):
    def __init__(self, queue_collection):
        self._queue = AgentTxQueue()
        self._queue_collection = queue_collection

    def on_message(self, message):
        log.debug("AmqpTxForwarder.on_message: %s/%s/%s %s" % (
            message['fqdn'],
            message['plugin'],
            message['session_id'],
            message['type']))
        self._queue_collection.send(message)

    def run(self):
        self._queue.serve(self.on_message)

    def stop(self):
        self._queue.stop()
