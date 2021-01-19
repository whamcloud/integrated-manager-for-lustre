# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""RPC facility for use in ChromaService services.

The outward facing parts of this module are the `ServiceRpc` class and the
RpcWaiter.initialize/shutdown methods.

Concurrent RPC invocations from a single process are handled by a global
instance of RpcWaiter, which requires explicit initialization and shutdown.
This is taken care of if your code is running within the `chroma_service`
management command.
"""
import logging

import socket
import threading
import uuid
import django
import errno
import os
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
        "request_id": {"type": "string"},
        "method": {"type": "string"},
        "args": {"type": "array"},
        "kwargs": {"type": "object"},
        "response_routing_key": {"type": "string"},
    },
    "required": ["request_id", "method", "args", "kwargs", "response_routing_key"],
}

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "exception": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "result": {},
        "request_id": {"type": "string"},
    },
    "required": ["exception", "result", "request_id"],
}

RESPONSE_TIMEOUT = 300

"""
Max number of lightweight RPCs that can be in flight concurrently.  This must
be well within the rabbitmq server's connection limit

"""
LIGHTWEIGHT_CONNECTIONS_LIMIT = 10


RESPONSE_CONN_LIMIT = 10

tx_connections = None
rx_connections = None
lw_connections = None

log = log_register("rpc")


class RpcError(Exception):
    def __init__(self, description, exception_type, **kwargs):
        super(Exception, self).__init__(description)
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

    def __init__(self, rpc, body, response_conn_pool):
        super(RunOneRpc, self).__init__()
        self.rpc = rpc
        self.body = body
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

                maybe_declare(_amqp_exchange(), producer.channel, True, **retry_policy)
                producer.publish(
                    result,
                    serializer="json",
                    routing_key=self.body["response_routing_key"],
                    delivery_mode=TRANSIENT_DELIVERY_MODE,
                    retry=True,
                    retry_policy=retry_policy,
                    immedate=True,
                    mandatory=True,
                )


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
            RunOneRpc(self.rpc, body, self._response_conn_pool).start()

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


class RpcClientResponseHandler(threading.Thread):
    """Handle responses for a particular named RPC service."""

    def __init__(self, response_routing_key):
        super(RpcClientResponseHandler, self).__init__()
        self._stopping = False
        self._response_states = {}
        self._response_routing_key = response_routing_key

        self._started = threading.Event()

    def wait_for_start(self):
        """During initialization, caller needs to be able to block
        on the handler thread starting up, to avoid attempting to issue
        RPCs before the response handler is available

        """
        self._started.wait()

    def start_wait(self, request_id, rpc_timeout):
        log.debug("start_wait %s" % request_id)
        self._response_states[request_id] = ResponseWaitState(rpc_timeout)

    def complete_wait(self, request_id):
        log.debug("complete_wait %s" % request_id)
        state = self._response_states[request_id]
        state.complete.wait()
        log.debug("complete_wait %s triggered" % request_id)

        del self._response_states[request_id]

        if state.timeout:
            raise RpcTimeout()
        else:
            return state.result

    def _age_response_states(self):
        # FIXME: keep a sorted list by insertion time to avoid
        # the need to check all the timeouts
        t = time.time()
        for request_id, state in self._response_states.items():
            if not state.complete.is_set() and t > state.timeout_at:
                log.debug("Aged out RPC %s" % request_id)
                state.timeout = True
                state.complete.set()

    def timeout_all(self):
        for request_id, state in self._response_states.items():
            state.timeout = True
            state.complete.set()

    def run(self):
        log.debug("ResponseThread.run")

        def callback(body, message):
            # log.debug(body)
            try:
                jsonschema.validate(body, RESPONSE_SCHEMA)
            except jsonschema.ValidationError as e:
                log.error("Malformed response: %s" % e)
            else:
                try:
                    state = self._response_states[body["request_id"]]
                except KeyError:
                    log.debug("Unknown request ID %s" % body["request_id"])
                else:
                    state.result = body
                    state.complete.set()
            finally:
                message.ack()

        with rx_connections[_amqp_connection()].acquire(block=True) as connection:
            # Prepare the response queue
            with connection.Consumer(
                queues=[
                    kombu.messaging.Queue(
                        self._response_routing_key,
                        _amqp_exchange(),
                        routing_key=self._response_routing_key,
                        auto_delete=True,
                        durable=False,
                    )
                ],
                callbacks=[callback],
            ):

                self._started.set()
                while not self._stopping:
                    try:
                        connection.drain_events(timeout=1)
                    except socket.timeout:
                        pass
                    except IOError as e:
                        #  See HYD-2551
                        if e.errno != errno.EINTR:
                            # if not [Errno 4] Interrupted system call
                            raise

                    self._age_response_states()

        log.debug("%s stopped" % self.__class__.__name__)

    def stop(self):
        log.debug("%s stopping" % self.__class__.__name__)
        self._stopping = True


class RpcClient(object):
    """
    One instance of this is created for each named RPC service
    that this process calls into.

    """

    def __init__(self, service_name, lightweight=False):
        self._service_name = service_name
        self._request_routing_key = "%s.requests" % self._service_name
        self._lightweight = lightweight
        if not self._lightweight:
            self._response_routing_key = "%s.responses_%s_%s" % (self._service_name, os.uname()[1], os.getpid())
            self.response_thread = RpcClientResponseHandler(self._response_routing_key)
            self.response_thread.start()
            self.response_thread.wait_for_start()

    def stop(self):
        if not self._lightweight:
            self.response_thread.stop()

    def join(self):
        if not self._lightweight:
            self.response_thread.join()

    def timeout_all(self):
        if not self._lightweight:
            self.response_thread.timeout_all()

    def _send(self, connection, request):
        """
        :param request: JSON serializable dict

        """
        dbutils.exit_if_in_transaction(log)
        log.debug("send %s" % request["request_id"])
        request["response_routing_key"] = self._response_routing_key

        def errback(exc, _):
            log.info("RabbitMQ rpc got a temporary error. May retry. Error: %r", exc, exc_info=1)

        retry_policy = {"max_retries": 10, "errback": errback}

        with Producer(connection) as producer:
            maybe_declare(_amqp_exchange(), producer.channel, True, **retry_policy)
            producer.publish(
                request,
                serializer="json",
                routing_key=self._request_routing_key,
                delivery_mode=TRANSIENT_DELIVERY_MODE,
                retry=True,
                retry_policy=retry_policy,
            )

    def call(self, request, rpc_timeout=RESPONSE_TIMEOUT):
        request_id = request["request_id"]

        if not self._lightweight:
            self.response_thread.start_wait(request_id, rpc_timeout)
            with tx_connections[_amqp_connection()].acquire(block=True) as connection:
                self._send(connection, request)
            return self.response_thread.complete_wait(request_id)
        else:
            self._response_routing_key = "%s.responses_%s_%s_%s" % (
                self._service_name,
                os.uname()[1],
                os.getpid(),
                request_id,
            )
            self._complete = False

            def callback(body, message):
                # log.debug(body)
                try:
                    jsonschema.validate(body, RESPONSE_SCHEMA)
                except jsonschema.ValidationError as e:
                    log.debug("Malformed response: %s" % e)
                else:
                    self._result = body
                    self._complete = True
                finally:
                    message.ack()

            with lw_connections[_amqp_connection()].acquire(block=True) as connection:
                with connection.Consumer(
                    queues=[
                        kombu.messaging.Queue(
                            self._response_routing_key,
                            _amqp_exchange(),
                            routing_key=self._response_routing_key,
                            auto_delete=True,
                            durable=False,
                        )
                    ],
                    callbacks=[callback],
                ):

                    self._send(connection, request)

                    timeout_at = time.time() + rpc_timeout
                    while not self._complete:
                        try:
                            connection.drain_events(timeout=1)
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


class RpcClientFactory(object):
    """
    Provide sending and receiving AMQP RPC messages on behalf of
    all concurrent operations within a process.

    This class creates and destroys RpcClient instances
    for each RPC service that this process makes calls to.

    This class operates either in a 'lightweight' mode or
    in a multi-threaded mode depending on whether `initialize_threads`
    is called.

    Lightweight mode does not spawn any additional threads to handle
    RPC responses, but has the overhead of creating separate AMQP connections
    for each concurrent RPC, and creating a separate response queue for each
    call.  This is for use in WSGI handlers performing comparatively rare
    operations (things that happen when a user clicks a button).

    Threaded mode spawns a response handler thread for each named RPC
    service that the calling process interacts with.  This reduces the number
    of queues and connections to one per service rather than one per call.  This
    is for use when issuing large numbers of concurrent RPCs, such as when
    performing a 1-per-server set of calls between backend processes.
    """

    _instances = {}
    _factory_lock = None
    _available = True

    _lightweight = True
    _lightweight_initialized = False

    @classmethod
    def initialize_threads(cls):
        """Set up for multi-threaded operation.  Calling this turns off
        'lightweight' mode, and causes the rpc module to use multiple
        threads when issuing RPCs.  If this is not called, then no
        extra threads are started when issuing RPCs

        """

        if not cls._lightweight:
            raise RuntimeError("Called %s.initialize_threads more than once!" % cls.__name__)
        log.debug("%s enabling multi-threading" % cls.__name__)

        # Cannot instantiate lock at module import scope because
        # it needs to happen after potential gevent monkey patching
        cls._factory_lock = threading.Lock()
        cls._lightweight = False

        global tx_connections
        global rx_connections
        tx_connections = kombu.pools.Connections(limit=10)
        rx_connections = kombu.pools.Connections(limit=20)

    @classmethod
    def shutdown_threads(cls):
        """Join any threads created.  Only necessary if `initialize` was called"""
        assert not cls._lightweight
        with cls._factory_lock:
            for instance in cls._instances.values():
                instance.stop()
            for instance in cls._instances.values():
                instance.join()
            for instance in cls._instances.values():
                instance.timeout_all()

            cls._available = False

    @classmethod
    def get_client(cls, queue_name):
        if cls._lightweight:
            if not cls._lightweight_initialized:
                # connections.limit = LIGHTWEIGHT_CONNECTIONS_LIMIT
                global lw_connections
                lw_connections = kombu.pools.Connections(limit=LIGHTWEIGHT_CONNECTIONS_LIMIT)
                cls._lightweight_initialized = True
            return RpcClient(queue_name, lightweight=True)
        else:
            with cls._factory_lock:
                if not cls._available:
                    raise RuntimeError("Attempted to acquire %s instance after shutdown" % cls.__name__)

                try:
                    instance = cls._instances[queue_name]
                except KeyError:
                    log.debug("Instantiating RpcWaiter for %s" % queue_name)
                    instance = RpcClient(queue_name)
                    cls._instances[queue_name] = instance

            return instance


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

        rpc_client = RpcClientFactory.get_client(self.__class__.__name__)

        result = rpc_client.call(request, rpc_timeout)

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
        with _amqp_connection() as connection:
            self.worker = RpcServer(self, connection, self.__class__.__name__)
            self.worker.run()

    def stop(self):
        # self.worker could be None if thread stopped before run() gets to the point of setting it
        if self.worker is not None:
            self.worker.stop()
