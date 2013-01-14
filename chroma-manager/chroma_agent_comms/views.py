#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import Queue
import json
import M2Crypto
from chroma_core.models import ManagedHost
from chroma_core.models.utils import Version
from chroma_core.services import log_register
from chroma_core.services.http_agent.crypto import Crypto

from django.http import HttpResponseNotAllowed, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
import settings


log = log_register('agent_views')


class MessageView(View):
    queues = None
    sessions = None
    hosts = None

    LONG_POLL_TIMEOUT = 30

    def post(self, request):
        """
        Receive messages FROM the agent.
        Handle a POST containing messages from the agent
        """
        body = json.loads(request.body)
        fqdn = request.META['HTTP_X_SSL_CLIENT_NAME']
        messages = body['messages']

        #self.hosts.update(fqdn)
        log.debug("MessageView.post: %s %s messages" % (fqdn, len(messages)))
        for message in messages:
            if message['type'] == 'DATA':
                try:
                    self.sessions.get(fqdn, message['plugin'], message['session_id'])
                except KeyError:
                    log.warning("Terminating session because unknown %s/%s/%s" % (fqdn, message['plugin'], message['session_id']))
                    self.queues.send(fqdn, {
                        'type': 'SESSION_TERMINATE',
                        'plugin': message['plugin'],
                        'session_id': message['session_id'],
                        'session_seq': None,
                        'body': None
                    })
                else:
                    log.debug("Forwarding valid message %s/%s/%s-%s" % (fqdn, message['plugin'], message['session_id'], message['session_seq']))
                    self.queues.receive(fqdn, message)

            elif message['type'] == 'SESSION_CREATE_REQUEST':
                session = self.sessions.create(fqdn, message['plugin'])
                log.info("Creating session %s/%s/%s" % (fqdn, message['plugin'], session.id))
                self.queues.send(fqdn, {
                    'type': 'SESSION_CREATE_RESPONSE',
                    'plugin': session.plugin,
                    'session_id': session.id,
                    'session_seq': None,
                    'body': None
                })

        return HttpResponse()

    def get(self, request):
        """
        Send messages TO the agent.
        Handle a long-polling GET for messages to the agent
        """

        fqdn = request.META['HTTP_X_SSL_CLIENT_NAME']
#        server_boot_time = dateutil.parser.parse(request.GET['server_boot_time'])
#        client_start_time = dateutil.parser.parse(request.GET['client_start_time'])

        payload = []

# FIXME: host_state is doing writes to ManagedHost, which is deadlocking with job_scheduler
# during the host setup immediately after registration.
#        # If server_boot_time has changed, then the server has rebooted
#        reset_required = self.hosts.update(fqdn, server_boot_time, client_start_time)
#        if reset_required:
#            # This is the case where the http_agent service restarts, so
#            # we have to let the agent know that all open sessions
#            # are now over.
#            payload.append({
#                'type': 'SESSION_TERMINATE_ALL',
#                'plugin': None,
#                'session_id': None,
#                'session_seq': None,
#                'body': None
#            })

        log.info("MessageView.get: composing messages for %s" % fqdn)
        queue = self.queues.get(fqdn).tx
        log.debug("MessageView.get: waiting for queue %s/%s" % (fqdn, queue))

        try:
            first_message = queue.get(block = True, timeout = self.LONG_POLL_TIMEOUT)
        except Queue.Empty:
            pass
        else:
            # TODO: limit number of messages per response
            payload.append(first_message)
            while True:
                try:
                    payload.append(queue.get(block = False))
                except Queue.Empty:
                    break

                    # TODO: filter the returned message such that all DATA Messages
                    # have the current session ID, or are dropped

        log.info("MessageView.get: responding to %s with %s messages" % (fqdn, len(payload)))
        return HttpResponse(json.dumps({'messages': payload}), mimetype = "application/json")


@csrf_exempt
def register(request, key = None):
    if request.method != "POST":
        return HttpResponseNotAllowed(['POST'])

    # TODO: validate the key against one issued via the API
    # Test that the host is registering using a URL containing
    # a known key
    host_attributes = json.loads(request.body)

    # Fail at the first if the version of the agent on the server is incorrect
    manager, agent = Version(settings.VERSION), Version(host_attributes['version'])
    if manager and agent and not (manager.major == agent.major and manager.minor >= agent.minor):
        return HttpResponse(status = 400, content = "Version incompatibility between manager {0} and agent {1}".format(manager, agent))

    # Fulfil the registering server's request for a certificate authenticating
    # it as the owner of this FQDN.
    csr = host_attributes['csr']
    certificate_str = Crypto().sign(csr)
    certificate = M2Crypto.X509.load_cert_string(certificate_str, M2Crypto.X509.FORMAT_PEM)
    fingerprint = certificate.get_fingerprint(md = 'sha1')

    # Check that the commonName in the CSR is the same as that in host_attributes
    # (prevent registering as one host and getting a certificate to impersonate another)
    csr_fqdn = certificate.get_subject().commonName
    if csr_fqdn != host_attributes['fqdn']:
        # Terse response to attacker
        log.error("FQDN mismatch '%s' vs. '%s' from %s" % (csr_fqdn, host_attributes['fqdn'], request.META['HTTP_X_FORWARDED_FOR']))
        return HttpResponse(status = 400, content = "")

    # FIXME: handle the case where someone registers,
    # and then dies before saving their certificate:
    # when they come through here again, currently
    # we'll reject them because the FQDN is taken
    # ... maybe hand back the certificate here, but
    # then don't create the host until they first
    # connect using the certificate?
    # in that case to avoid handing out another cert
    # to someone else spamming our URL, we should have
    # some logic during the second addition to revoke
    # the first (should never be used) host cert.

    host, command = ManagedHost.create(
        address = host_attributes['address'],
        fqdn = host_attributes['fqdn'],
        nodename = host_attributes['nodename'],
        capabilities = host_attributes['capabilities'],
        ssl_fingerprint = fingerprint
    )

    # TODO: document this return format
    return HttpResponse(status = 201, content = json.dumps({
        'command_id': command.id,
        'host_id': host.id,
        'certificate': certificate_str
    }), mimetype = "application/json")
