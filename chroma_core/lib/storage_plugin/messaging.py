
# TODO connection caching
from kombu import BrokerConnection, Exchange, Queue
import socket
import settings
import datetime

from chroma_core.lib.storage_plugin.log import storage_plugin_log as log


def _drain_all(connection, queue, handler, timeout = 0.1):
    """Helper for draining all messages on a particular queue
    (kombo's inbuilt drain_events generally just gives you one)

    Waits either for timeout, or until at least one message has been
    accepted and the queue is empty.

    handler: return True if you got something valid/expected, return False
    otherwise (used for returning soon if the queue goes empty and something
    valid has been received).
    """
    # NB using a list instead of just a boolean in order to get
    # a reference into the handler function
    any_accepted = []

    def local_handler(body, message):
        if handler(body, message):
            any_accepted.append(True)

    latency = 0.5
    started = datetime.datetime.now()
    with connection.Consumer([queue], callbacks=[local_handler]):
        # Loop until we get a call to drain_events which
        # does not result in a handler callback
        while True:
            exhausted = False
            try:
                connection.drain_events(timeout = latency)
            except socket.timeout:
                exhausted = True
                pass

            elapsed = datetime.datetime.now() - started
            if (exhausted and any_accepted) or (exhausted and elapsed > datetime.timedelta(seconds = timeout)):
                break


def _amqp_connection():
    return BrokerConnection("amqp://%s:%s@%s:%s/%s" % (
        settings.BROKER_USER,
        settings.BROKER_PASSWORD,
        settings.BROKER_HOST,
        settings.BROKER_PORT,
        settings.BROKER_VHOST))


def simple_send(name, body):
    with _amqp_connection() as conn:
        q = conn.SimpleQueue(name, serializer = 'json')
        q.put(body)


def simple_receive(name):
    with _amqp_connection() as conn:
        q = conn.SimpleQueue(name, serializer = 'json')
        from Queue import Empty
        try:
            message = q.get(block = False)
            message.ack()
            return message.decode()
        except Empty:
            return None


def _wait_for_host(host, timeout):
    #: How often to check the host to see if it has become available
    UNAVAILABLE_POLL_INTERVAL = 10
    unavailable_elapsed = 0
    while not host.is_available():
        # Polling delay
        import time
        time.sleep(UNAVAILABLE_POLL_INTERVAL)

        # Apply the timeout if one is set
        unavailable_elapsed += UNAVAILABLE_POLL_INTERVAL
        if timeout and unavailable_elapsed >= timeout:
            raise Timeout("Timed out waiting for host %s to become available" % (host))

        # Reload the ManagedHost from the database
        from django.db import transaction
        from chroma_core.models.host import ManagedHost
        with transaction.commit_manually():
            transaction.commit()
            host = ManagedHost.objects.get(pk=host.id)
            transaction.commit()


def plugin_rpc(plugin_name, host, request, timeout = 0):
    """
    :param plugin_name: String name of plugin
    :param host: ManagedHost instance
    :param request: JSON-serializable dict
    :param timeout: If None (default) then block until the Host is available for requests
    """

    # See if there are any request_id=None responses enqueued: these are used
    # when we want to pre-populate some data for a plugin (e.g. 'linux' and device detection)
    try:
        result = PluginResponse.receive(plugin_name, host.fqdn, None, timeout = 0.1)
        return result
    except Timeout:
        pass

    # If the host is not available, don't submit a request until it is available
    if not host.is_available():
        log.info("Host %s is not available for plugin RPC, waiting" % host)
        _wait_for_host(host, timeout)
        log.info("Host %s is now available for plugin RPC" % host)

    # The host is available and there were no out-of-band responses to
    # use, so we will send a request.
    request_id = PluginRequest.send(plugin_name, host.fqdn, {})
    try:
        return PluginResponse.receive(plugin_name, host.fqdn, request_id)
    except Timeout:
        # Revoke the request, we will never handle a response from it
        PluginRequest.revoke(plugin_name, host.fqdn, request_id)
        raise


def rpc(queue_name, kwargs):
    request_id = PluginRequest.send(queue_name, "", kwargs)
    try:
        return PluginResponse.receive(queue_name, "", request_id)
    except Timeout:
        # Revoke the request, we will never handle a response from it
        PluginRequest.revoke(queue_name, "", request_id)
        raise


class Timeout(Exception):
    pass


class PluginRequest(object):
    @classmethod
    def send(cls, plugin_name, resource_tag, request_dict, timeout = None):
        request_id = None
        with _amqp_connection() as conn:
            conn.connect()

            exchange = Exchange("plugin_data", "direct", durable = True)

            # Send a request for information from the plugin on this host
            request_routing_key = "plugin_data_request_%s_%s" % (plugin_name, resource_tag)

            # Compose the body
            import uuid
            request_id = uuid.uuid1().__str__()
            body = {'id': request_id}
            for k, v in request_dict.items():
                if k == 'id':
                    raise RuntimeError("Cannot use 'id' in PluginRequest body")
                body[k] = v

            with conn.Producer(exchange = exchange, serializer = 'json', routing_key = request_routing_key) as producer:
                producer.publish(body)
            log.info("Sent request for %s (%s)" % (request_routing_key, request_id))

        return request_id

    @classmethod
    def receive_all(cls, plugin_name, resource_tag):
        """Ack all waiting requests and return them in a list"""
        requests = []

        def handler(body):
            log.info("UpdateScan %s: Passing on request %s" % (resource_tag, body['id']))
            requests.append(body)

        cls.handle_all(plugin_name, resource_tag, handler)

        return requests

    @classmethod
    def handle_all(cls, plugin_name, resource_tag, handler):
        """Invoke `handler` for each request before acking it"""
        exchange = Exchange("plugin_data", "direct", durable = True)
        with _amqp_connection() as conn:
            conn.connect()
            # See if there are any requests for this agent plugin
            request_routing_key = "plugin_data_request_%s_%s" % (plugin_name, resource_tag)

            def handle_request(body, message):
                result = handler(body)
                message.ack()
                return result

            request_queue = Queue(request_routing_key, exchange = exchange, routing_key = request_routing_key)
            request_queue(conn.channel()).declare()

            _drain_all(conn, request_queue, handle_request)

    @classmethod
    def revoke(cls, plugin_name, resource_tag, request_id):
        exchange = Exchange("plugin_data", "direct", durable = True)
        with _amqp_connection() as conn:
            conn.connect()
            # See if there are any requests for this agent plugin
            request_routing_key = "plugin_data_request_%s_%s" % (plugin_name, resource_tag)

            requests = []

            def handle_request(body, message):
                if body['id'] == request_id:
                    message.ack()

            request_queue = Queue(request_routing_key, exchange = exchange, routing_key = request_routing_key)
            request_queue(conn.channel()).declare()
            with conn.Consumer([request_queue], callbacks=[handle_request]):
                from socket import timeout
                try:
                    conn.drain_events(timeout = 0.1)
                except timeout:
                    pass
        return requests


# TODO: couple this timeout to the HTTP reporting interval
DEFAULT_RESPONSE_TIMEOUT = 30


class PluginResponse(object):
    @classmethod
    def send(cls, plugin_name, resource_tag, request_id, response_data):
        exchange = Exchange("plugin_data", "direct", durable = True)
        with _amqp_connection() as conn:
            conn.connect()
            response_routing_key = "plugin_data_response_%s_%s" % (plugin_name, resource_tag)
            with conn.Producer(exchange = exchange, serializer = 'json', routing_key = response_routing_key) as producer:
                producer.publish({'id': request_id, 'data': response_data})

    @classmethod
    def receive(cls, plugin_name, resource_tag, request_id, timeout = DEFAULT_RESPONSE_TIMEOUT):
        """request_id may be None to marge any response"""
        with _amqp_connection() as conn:
            conn.connect()

            exchange = Exchange("plugin_data", "direct", durable = True)

            log.info("Waiting for response for %s:%s:%s" % (plugin_name, resource_tag, request_id))
            exchange = Exchange("plugin_data", "direct", durable = True)
            response_routing_key = "plugin_data_response_%s_%s" % (plugin_name, resource_tag)
            response_queue = Queue(response_routing_key, exchange = exchange, routing_key = response_routing_key)
            response_queue(conn.channel()).declare()
            response_data = []

            def handle_response(body, message):
                accepted = False
                try:
                    id = body['id']
                except KeyError:
                    import json
                    log.warning("Malformed response '%s' on %s" % (json.dumps(body), response_routing_key))
                else:
                    if id == request_id:
                        response_data.append(body['data'])
                        log.info("Got response for request %s" % request_id)
                        accepted = True
                    else:
                        log.warning("Dropping unexpected response %s on %s" % (id, response_routing_key))
                finally:
                    message.ack()

                return accepted

            _drain_all(conn, response_queue, handle_response, timeout = timeout)
            if len(response_data) > 0:
                return response_data[0]
            else:
                raise Timeout("Got no response for %s:%s:%s in %s seconds" % (plugin_name, resource_tag, request_id, timeout))
