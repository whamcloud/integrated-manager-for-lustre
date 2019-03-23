# Copyright (c) 2019 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
RPC facility for use in ChromaService services.

The outward facing part of this module is the `ServiceRpc` class.
"""

import logging
import socket
import threading
import uuid
import django
import errno
import time
import jsonschema
import kombu
import kombu.pools
from kombu.common import maybe_declare
from kombu.mixins import ConsumerMixin
from kombu.messaging import Queue, Producer
from kombu.entity import TRANSIENT_DELIVERY_MODE

from chroma_core.services.log import log_register
from chroma_core.services import _amqp_connection, _amqp_exchange, dbutils


REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "request_id": {"type": "string", "required": True},
        "method": {"type": "string", "required": True},
        "args": {"type": "array", "required": True},
        "kwargs": {"type": "object", "required": True},
    },
}


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "exception": {"type": ["string", "null"], "required": True},
        "result": {"required": True},
        "request_id": {"type": "string", "required": True},
    },
}

RESPONSE_TIMEOUT = 300
RESPONSE_CONN_LIMIT = 10

log = log_register("rpc")


class RpcError(Exception):
    def __init__(self, description, exception_type, **kwargs):
        super(RpcError, self).__init__(description)
        self.description = description
        self.remote_exception_type = exception_type
        self.traceback = kwargs.get("traceback")

    def __str__(self):
        return "RpcError: %s" % self.description


class RpcTimeout(Exception):
    pass


class RunOneRpc(threading.Thread):
    """Handle a single incoming RPC in a new thread, and send the
    response (result or exception) from the execution thread."""

    def __init__(self, rpc, body, routing_key, response_conn_pool):
        super(RunOneRpc, self).__init__()
        self.rpc = rpc
        self.body = body
        self.routing_key = routing_key
        self._response_conn_pool = response_conn_pool

    def run(self):
        try:
            result = {
                "result": self.rpc._local_call(self.body["method"], *self.body["args"], **self.body["kwargs"]),
                "request_id": self.body["request_id"],
                "exception": None,
            }
        except Exception as e:
            import sys
            import traceback

            exc_info = sys.exc_info()
            backtrace = "\n".join(traceback.format_exception(*(exc_info or sys.exc_info())))

            # Utility to generate human readable errors
            def translate_error(err):
                from socket import error as socket_error

                if type(err) == socket_error:
                    return "Cannot reach server"

                return str(err)

            result = {
                "request_id": self.body["request_id"],
                "result": None,
                "exception": translate_error(e),
                "exception_type": type(e).__name__,
                "traceback": backtrace,
            }
            log.error("RunOneRpc: exception calling %s: %s" % (self.body["method"], backtrace))
        finally:
            django.db.connection.close()

        with self._response_conn_pool[_amqp_connection()].acquire(block=True) as connection:

            def errback(exc, _):
                log.info("RabbitMQ rpc got a temporary error. May retry. Error: %r", exc, exc_info=1)

            retry_policy = {"max_retries": 10, "errback": errback}

            connection.ensure_connection(**retry_policy)

            with Producer(connection) as producer:

                producer.publish(result, serializer="json", routing_key=self.routing_key)


class RpcServer(ConsumerMixin):
    def __init__(self, rpc, connection, service_name, serialize=False):
        """
        :param rpc: A ServiceRpcInterface instance
        :param serialize: If True, then process RPCs one after another in a single thread
        rather than running a thread for each RPC.
        """
        super(RpcServer, self).__init__()
        self.serialize = serialize
        self.rpc = rpc
        self.connection = connection
        self.queue_name = service_name
        self.request_routing_key = "%s.requests" % self.queue_name
        self._response_conn_pool = kombu.pools.Connections(limit=RESPONSE_CONN_LIMIT)

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(
                queues=[
                    Queue(
                        self.request_routing_key, _amqp_exchange(), routing_key=self.request_routing_key, durable=False
                    )
                ],
                callbacks=[self.process_task],
            )
        ]

    def process_task(self, body, message):
        message.ack()

        try:
            jsonschema.validate(body, REQUEST_SCHEMA)
        except jsonschema.ValidationError as e:
            # Don't even try to send an exception response, because validation failure
            # breaks our faith in request_id and response_routing_key
            log.error("Invalid RPC body: %s" % e)
        else:
            routing_key = message.properties["reply_to"]
            RunOneRpc(self.rpc, body, routing_key, self._response_conn_pool).start()

    def stop(self):
        self.should_stop = True


class ResponseWaitState(object):
    """State kept by for each outstanding RPC -- the response handler
    must first populate result, then set the `complete` event."""

    def __init__(self, rpc_timeout):
        self.complete = threading.Event()
        self.timeout = False
        self.result = None
        self.timeout_at = time.time() + rpc_timeout


class RpcClient(object):
    """
    One instance of this is created for each named RPC service
    that this process calls into.

    """

    def __init__(self, service_name, connection, channel, lock):
        self._service_name = service_name
        self._request_routing_key = "%s.requests" % self._service_name
        self._connection = connection
        self._channel = channel
        self._lock = lock

    def _send(self, channel, request):
        """
        :param request: JSON serializable dict

        """
        dbutils.exit_if_in_transaction(log)
        log.debug("send %s" % request["request_id"])

        def errback(exc, _):
            log.info("RabbitMQ rpc got a temporary error. May retry. Error: %r", exc, exc_info=1)

        retry_policy = {"max_retries": 10, "errback": errback}

        with self._lock:
            producer = Producer(channel)

            try:
                maybe_declare(_amqp_exchange(), channel, True, **retry_policy)
                producer.publish(
                    request,
                    serializer="json",
                    routing_key=self._request_routing_key,
                    delivery_mode=TRANSIENT_DELIVERY_MODE,
                    retry=True,
                    retry_policy=retry_policy,
                    reply_to="amq.rabbitmq.reply-to",
                )
            finally:
                producer.release()

    def call(self, request, rpc_timeout=RESPONSE_TIMEOUT):
        self._complete = False

        def callback(body, message):
            try:
                jsonschema.validate(body, RESPONSE_SCHEMA)
            except jsonschema.ValidationError as e:
                log.debug("Malformed response: %s" % e)
            else:
                self._result = body
                self._complete = True
            finally:
                message.ack()

        with self._lock:
            consumer = kombu.Consumer(
                self._channel,
                queues=[kombu.messaging.Queue("amq.rabbitmq.reply-to", no_ack=True)],
                callbacks=[callback],
            )

        try:
            with self._lock:
                consumer.consume()

            self._send(self._channel, request)

            timeout_at = time.time() + rpc_timeout
            while not self._complete:
                try:
                    with self._lock:
                        self._connection.drain_events(timeout=1)
                except socket.timeout:
                    pass
                except IOError as e:
                    #  See HYD-2551
                    if e.errno != errno.EINTR:
                        # if not [Errno 4] Interrupted system call
                        raise
                if time.time() > timeout_at:
                    raise RpcTimeout()

            return self._result
        finally:
            with self._lock:
                consumer.cancel()


class RpcClientFactory(object):
    """
    Provide sending and receiving AMQP RPC messages on behalf of
    all concurrent operations within a process.

    This class creates and destroys RpcClient instances
    for each RPC service that this process makes calls to.

    This class does not spawn any additional threads to handle
    RPC responses, instead it uses direct reply-to (https://www.rabbitmq.com/direct-reply-to.html) to ensure
    no additional queues are created.

    Connections passed into this factory should be reused,
    only channels should be variant
    """

    @classmethod
    def get_client(cls, queue_name, connection, channel, lock):
        return RpcClient(queue_name, connection, channel, lock)


class Noop:
    def __init__(self):
        pass

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass


if kombu.utils.compat.detect_environment() == "gevent":
    from gevent.lock import Semaphore

    lock = Semaphore()
else:
    lock = Noop()


conn = _amqp_connection()


class ServiceRpcInterface(object):
    """Create a class inheriting from this to expose some methods of another
    class for RPC.  In your subclass, define the `methods` class attribute with a list
    of RPC-callable attributes.

    If you have a class `foo` and you want to expose some methods to the world:

    ::

        class Foo(object):
          def functionality(self):
            pass

        class FooRpc(ServiceRpcInterface):
          methods = ['functionality']

        server = FooRpc(Foo())
        server.run()

    To invoke this method from another process:

    ::

        FooRpc().functionality()

    """

    _connection = conn
    _lock = lock

    def __init__(self, wrapped=None):
        self.worker = None
        self.wrapped = wrapped

        if wrapped:
            # Raise an exception if any of the declared methods don't exist
            # on the wrapped object
            for method in self.methods:
                getattr(wrapped, method)

    def __getattr__(self, name):
        if name in self.methods:
            return lambda *args, **kwargs: self._call(name, *args, **kwargs)
        else:
            raise AttributeError(name)

    def _call(self, fn_name, *args, **kwargs):
        # If the caller specified rcp_timeout then fetch it from the args and remove.
        rpc_timeout = kwargs.pop("rpc_timeout", RESPONSE_TIMEOUT)

        request_id = uuid.uuid4().__str__()
        request = {"method": fn_name, "args": args, "kwargs": kwargs, "request_id": request_id}

        log.debug("Starting rpc: %s, id: %s " % (fn_name, request_id))
        log.debug("_call: %s %s %s %s" % (request_id, fn_name, args, kwargs))

        with self._lock:
            chan = self._connection.channel()

        try:
            rpc_client = RpcClientFactory.get_client(self.__class__.__name__, self._connection, chan, self._lock)

            result = rpc_client.call(request, rpc_timeout)
        finally:
            with self._lock:
                chan.close()

        if result["exception"]:
            log.error(
                "ServiceRpcInterface._call: exception %s: %s \ttraceback: %s"
                % (result["exception"], result["exception_type"], result.get("traceback"))
            )
            raise RpcError(result["exception"], result.get("exception_type"), traceback=result.get("traceback"))
        else:
            # NB: 'result' can be very large, and almost cripple the various logs where
            # rpcs are run: http.log, job_scheduler.log, etc.
            # If you want to see response result data from rpcs at the INFO level, consider writing
            # log messages into the JobSchedulerClient calls.  Leaving this in for DEBUG.

            if log.getEffectiveLevel() is not logging.DEBUG:
                # Truncate message
                result100 = str(result)[:100]
                if str(result) != result100:
                    result100 += "..."
                result_str = result100
            else:
                result_str = result

            log.debug("Completed rpc: %s, id: %s, result: %s" % (fn_name, request_id, result_str))

            return result["result"]

    def _local_call(self, fn_name, *args, **kwargs):
        log.debug("_local_call: %s %s %s" % (fn_name, args, kwargs))
        assert fn_name in self.methods
        fn = getattr(self.wrapped, fn_name)
        return fn(*args, **kwargs)

    def run(self):
        self.worker = RpcServer(self, self._connection, self.__class__.__name__)
        self.worker.run()

    def stop(self):
        log.info("Stopping ServiceRpcInterface")
        # self.worker could be None if thread stopped before run() gets to the point of setting it
        if self.worker is not None:
            self.worker.stop()

        with self._lock:
            self._connection.release()
