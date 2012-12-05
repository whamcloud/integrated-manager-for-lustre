#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent_comms.views import AmqpTxForwarder, AmqpRxForwarder, _queues, _sessions
from chroma_core.services.http_agent import AgentSessionRpc
from django.core.handlers.wsgi import WSGIHandler
from chroma_core.services import ChromaService, ServiceThread
from cherrypy import wsgiserver


class Service(ChromaService):
    def run(self):
        raise RuntimeError()

        self.amqp_tx_forwarder = AmqpTxForwarder(_queues)
        self.amqp_rx_forwarder = AmqpRxForwarder(_queues)

        tx_svc_thread = ServiceThread(self.amqp_tx_forwarder)
        rx_svc_thread = ServiceThread(self.amqp_rx_forwarder)
        rx_svc_thread.start()
        tx_svc_thread.start()

        session_rpc_thread = ServiceThread(AgentSessionRpc(_sessions))
        session_rpc_thread.start()

        self.server = wsgiserver.CherryPyWSGIServer(
            ("0.0.0.0", 8001), WSGIHandler(), numthreads = 100)
        self.server.start()

        session_rpc_thread.stop()
        tx_svc_thread.stop()
        rx_svc_thread.stop()
        session_rpc_thread.join()
        tx_svc_thread.join()
        tx_svc_thread.join()

    def stop(self):
        self.server.stop()
