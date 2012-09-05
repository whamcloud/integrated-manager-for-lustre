#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.core.handlers.wsgi import WSGIHandler
from chroma_core.models.agent_session import AgentSession
from chroma_core.services import ChromaService
from cherrypy import wsgiserver


class Service(ChromaService):
    def start(self):
        AgentSession.objects.all().delete()

        self.server = wsgiserver.CherryPyWSGIServer(("0.0.0.0", 8000), WSGIHandler())
        self.server.start()

    def stop(self):
        self.server.stop()
