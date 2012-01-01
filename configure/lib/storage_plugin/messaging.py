
# TODO connection caching
from kombu import BrokerConnection, Exchange, Queue
import settings

from configure.lib.storage_plugin.log import storage_plugin_log as log


class PluginRequest(object):
    @classmethod
    def send(cls, plugin_name, resource_tag, request_dict):
        request_id = None
        with BrokerConnection("amqp://%s:%s@%s:%s/%s" % (settings.BROKER_USER, settings.BROKER_PASSWORD, settings.BROKER_HOST, settings.BROKER_PORT, settings.BROKER_VHOST)) as conn:
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
        exchange = Exchange("plugin_data", "direct", durable = True)
        with BrokerConnection("amqp://%s:%s@%s:%s/%s" % (settings.BROKER_USER, settings.BROKER_PASSWORD, settings.BROKER_HOST, settings.BROKER_PORT, settings.BROKER_VHOST)) as conn:
            conn.connect()
            # See if there are any requests for this agent plugin
            request_routing_key = "plugin_data_request_%s_%s" % (plugin_name, resource_tag)

            requests = []

            def handle_request(body, message):
                log.info("UpdateScan %s: Passing on request %s" % (resource_tag, body['id']))
                requests.append(body)
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


class PluginResponse(object):
    @classmethod
    def send(cls, plugin_name, resource_tag, request_id, response_data):
        exchange = Exchange("plugin_data", "direct", durable = True)
        with BrokerConnection("amqp://%s:%s@%s:%s/%s" % (settings.BROKER_USER, settings.BROKER_PASSWORD, settings.BROKER_HOST, settings.BROKER_PORT, settings.BROKER_VHOST)) as conn:
            conn.connect()
            response_routing_key = "plugin_data_response_%s_%s" % (plugin_name, resource_tag)
            with conn.Producer(exchange = exchange, serializer = 'json', routing_key = response_routing_key) as producer:
                producer.publish({'id': request_id, 'data': response_data})

    @classmethod
    def receive(cls, plugin_name, resource_tag, request_id):
        with BrokerConnection("amqp://%s:%s@%s:%s/%s" % (settings.BROKER_USER, settings.BROKER_PASSWORD, settings.BROKER_HOST, settings.BROKER_PORT, settings.BROKER_VHOST)) as conn:
            conn.connect()

            exchange = Exchange("plugin_data", "direct", durable = True)

            log.info("Waiting for response for %s:%s:%s" % (plugin_name, resource_tag, request_id))
            exchange = Exchange("plugin_data", "direct", durable = True)
            response_routing_key = "plugin_data_response_%s_%s" % (plugin_name, resource_tag)
            response_queue = Queue(response_routing_key, exchange = exchange, routing_key = response_routing_key)
            response_queue(conn.channel()).declare()
            response_data = []

            def handle_response(body, message):
                try:
                    id = body['id']
                except KeyError:
                    import json
                    log.warning("Malformed response '%s' on %s" % (json.dumps(body), response_routing_key))
                else:
                    if id == request_id:
                        response_data.append(body['data'])
                        log.warning("Got response for request %s" % request_id)
                    else:
                        log.warning("Dropping unexpected response %s on %s" % (id, response_routing_key))
                finally:
                    message.ack()

            # TODO: couple this timeout to the HTTP reporting interval
            RESPONSE_TIMEOUT = 30
            with conn.Consumer([response_queue], callbacks=[handle_response]):
                from socket import timeout
                exhausted = False
                while not exhausted:
                    try:
                        conn.drain_events(timeout = RESPONSE_TIMEOUT)
                    except timeout, e:
                        log.info("drain_events timeout %s" % e)
                        exhausted = True
            if len(response_data) > 0:
                return response_data[0]
            else:
                raise RuntimeError("Got no response for %s:%s:%s in %s seconds" % (plugin_name, resource_tag, request_id, RESPONSE_TIMEOUT))
