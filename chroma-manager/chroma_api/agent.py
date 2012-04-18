#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import dateutil.parser

from tastypie import fields
from tastypie.authorization import Authorization
from tastypie.authentication import Authentication
from tastypie.resources import Resource
from tastypie import http
from tastypie.exceptions import ImmediateHttpResponse

from chroma_api import api_log
from chroma_core.models import ManagedHost, AgentSession
from chroma_core.lib.lustre_audit import UpdateScan
from chroma_api.utils import custom_response
from django.http import HttpResponse

from chroma_core.lib.storage_plugin import messaging


class AgentResponse(object):
    def __init__(self):
        pass


class AgentResource(Resource):
    session = fields.DictField(null = True)
    body = fields.DictField(null = True)

    class Meta:
        object_class = AgentResponse
        authentication = Authentication()
        authorization = Authorization()
        list_allowed_methods = ['post']
        detail_allowed_methods = []
        resource_name = 'agent'

    def get_resource_uri(self, bundle):
        return ""

    def obj_create(self, bundle, request = None, **kwargs):
        try:
            host = ManagedHost.objects.get(fqdn = bundle.data['fqdn'])
        except ManagedHost.DoesNotExist:
            api_log.error("Request from unknown host %s" % bundle.data['fqdn'])
            raise ImmediateHttpResponse(response=http.HttpNotFound())

        if bundle.data['token'] != host.agent_token:
            api_log.error("Invalid token for host %s: %s" % (host, bundle.data['token']))
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        accept = False
        agent_session_id = bundle.data['session']['id']
        agent_session_counter = bundle.data['session']['counter']
        try:
            session = AgentSession.objects.get(host = host)
            if session.session_id == agent_session_id:
                accept = True
            else:
                api_log.info("Host %s connected with stale session ID %s (should be %s)" % (host, agent_session_id, session.session_id))
                session.delete()
                session = AgentSession.objects.create(host = host)
        except AgentSession.DoesNotExist:
            session = AgentSession.objects.create(host = host)
            api_log.info("Opened new session %s for %s" % (session.session_id, host))

        if accept:
            if agent_session_counter != session.counter:
                api_log.info("Bad session counter %s from host %s session %s (should be %s)" % (
                    agent_session_counter, host, session.id, session.counter))
                session.delete()
                session = AgentSession.objects.create(host = host)
            else:
                session.counter += 1
                session.save()

                updates = bundle.data['updates']
                api_log.debug("Received %d updates for session %s from %s" % (len(updates), session.session_id, host))

                # Special case for 'lustre' update, do not
                # pass it along to the storage plugin framework
                try:
                    lustre_data = updates.pop('lustre')
                    UpdateScan().run(host.id, dateutil.parser.parse(bundle.data['started_at']), lustre_data)
                except KeyError:
                    pass

                messaging.simple_send("agent", {
                    "session_id": session.session_id,
                    "host_id": host.id,
                    "updates": updates
                    })

        raise custom_response(self, request, HttpResponse, {'session_id': session.session_id})
