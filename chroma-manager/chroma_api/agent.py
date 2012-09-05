#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import datetime
import traceback
from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonQueue
import dateutil.parser
from dateutil import tz
import sys
from django.db import transaction

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
        always_return_data = True
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

                # Ensure the audit time is always respectably in the past to protect
                # against fast clocks on monitored servers
                latency_guess = datetime.timedelta(seconds = 1)
                started_at = dateutil.parser.parse(bundle.data['started_at'])
                sent_at = dateutil.parser.parse(bundle.data['sent_at'])

                now = datetime.datetime.utcnow().replace(tzinfo = tz.tzutc())
                if sent_at > now - latency_guess:
                    delta = sent_at - (now - latency_guess)
                    started_at -= delta

                # Special case for 'lustre' update, do not
                # pass it along to the storage plugin framework
                try:
                    lustre_data = updates.pop('lustre')
                except KeyError:
                    pass
                else:
                    try:
                        UpdateScan().run(host.id, started_at, lustre_data)
                    except Exception:
                        api_log.error("Error processing POST from %s: %s" % (
                            bundle.data['fqdn'],
                            '\n'.join(traceback.format_exception(*(sys.exc_info())))
                        ))

                        # If the client sends something which causes an exception,
                        # evict its session to prevent re-sending.
                        with transaction.commit_on_success():
                            session.delete()

                        raise

                AgentDaemonQueue().put({
                    "session_id": session.session_id,
                    "started_at": started_at.isoformat(),
                    "counter": session.counter,
                    "host_id": host.id,
                    "updates": updates
                    })

        raise custom_response(self, request, HttpResponse, {'session_id': session.session_id})
