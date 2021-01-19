# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


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
        queues = self.get(message["fqdn"])
        queues.tx.put(message)

    def receive(self, message):
        self.plugin_rx_queue.put(message)


class HostQueues(object):
    """Outgoing messages for a single host"""

    def __init__(self, fqdn):
        self.fqdn = fqdn
        self.tx = Queue.Queue()
        self.tx_lock = threading.Lock()


class AmqpRxForwarder(object):
    def __init__(self, queue_collection):
        self._stopping = threading.Event()
        self._queue_collection = queue_collection

    def run(self):
        with _amqp_connection() as conn:
            while not self._stopping.is_set():
                try:
                    msg = self._queue_collection.plugin_rx_queue.get(block=True, timeout=1)
                except Queue.Empty:
                    pass
                else:
                    plugin_name = msg["plugin"]
                    rx_queue_name = "agent_%s_rx" % plugin_name
                    q = conn.SimpleQueue(
                        rx_queue_name,
                        serializer="json",
                        exchange_opts={"durable": False},
                        queue_opts={"durable": False},
                    )
                    q.put(msg)

    def stop(self):
        self._stopping.set()


class AmqpTxForwarder(object):
    def __init__(self, queue_collection):
        self._queue = AgentTxQueue()
        self._queue_collection = queue_collection

    def on_message(self, message):
        log.debug(
            "AmqpTxForwarder.on_message: %s/%s/%s %s"
            % (message["fqdn"], message["plugin"], message["session_id"], message["type"])
        )
        self._queue_collection.send(message)

    def run(self):
        self._queue.serve(self.on_message)

    def stop(self):
        self._queue.stop()
