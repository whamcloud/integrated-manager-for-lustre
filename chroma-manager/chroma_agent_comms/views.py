#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import Queue
import json
import traceback
import datetime
import dateutil
import dateutil.tz

from django.db import transaction
from django.http import HttpResponseNotAllowed, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from functools import wraps
import settings
from tastypie.http import HttpForbidden

from chroma_core.models import ManagedHost, ClientCertificate
from chroma_core.models.utils import Version
from chroma_core.models.registration_token import RegistrationToken
from chroma_core.services import log_register
from chroma_core.services.http_agent.crypto import Crypto


log = log_register('agent_views')


def log_exception(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            return f(*args)
        except Exception:
            log.error(traceback.format_exc())
            raise

    return wrapped


class MessageView(View):
    queues = None
    sessions = None
    hosts = None

    LONG_POLL_TIMEOUT = 30

    @classmethod
    def valid_fqdn(cls, request):
        "Return fqdn if certificate is valid."
        fqdn = cls.valid_certs.get(request.META['HTTP_X_SSL_CLIENT_SERIAL'])
        if not fqdn:
            log.warning("Rejecting certificate %s" % request.META['HTTP_X_SSL_CLIENT_SERIAL'])
        elif fqdn != request.META['HTTP_X_SSL_CLIENT_NAME']:
            log.info("Domain name changed %s" % fqdn)
        return fqdn

    @log_exception
    def post(self, request):
        """
        Receive messages FROM the agent.
        Handle a POST containing messages from the agent
        """

        body = json.loads(request.body)
        fqdn = self.valid_fqdn(request)
        if not fqdn:
            return HttpForbidden()

        try:
            messages = body['messages']
        except KeyError:
            return HttpResponseBadRequest("Missing attribute 'messages'")

        # Check that the server identifier in each message
        # is valid by comparing against the SSL_CLIENT_NAME
        # which is cryptographically vouched for at the HTTPS frontend
        for message in messages:
            if message['fqdn'] != fqdn:
                return HttpResponseBadRequest("Incorrect client name")

        log.debug("MessageView.post: %s %s messages" % (fqdn, len(messages)))
        for message in messages:
            if message['type'] == 'DATA':
                try:
                    self.sessions.get(fqdn, message['plugin'], message['session_id'])
                except KeyError:
                    log.warning("Terminating session because unknown %s/%s/%s" % (fqdn, message['plugin'], message['session_id']))
                    self.queues.send({
                        'fqdn': fqdn,
                        'type': 'SESSION_TERMINATE',
                        'plugin': message['plugin'],
                        'session_id': None,
                        'session_seq': None,
                        'body': None
                    })
                else:
                    log.debug("Forwarding valid message %s/%s/%s-%s" % (fqdn, message['plugin'], message['session_id'], message['session_seq']))
                    self.queues.receive(message)

            elif message['type'] == 'SESSION_CREATE_REQUEST':
                session = self.sessions.create(fqdn, message['plugin'])
                log.info("Creating session %s/%s/%s" % (fqdn, message['plugin'], session.id))
                self.queues.send({
                    'fqdn': fqdn,
                    'type': 'SESSION_CREATE_RESPONSE',
                    'plugin': session.plugin,
                    'session_id': session.id,
                    'session_seq': None,
                    'body': None
                })

        return HttpResponse()

    def _filter_valid_messages(self, fqdn, messages):
        plugin_to_session_id = {}

        def is_valid(message):
            try:
                session_id = plugin_to_session_id[message['plugin']]
            except KeyError:
                try:
                    plugin_to_session_id[message['plugin']] = session_id = self.sessions.get(fqdn, message['plugin']).id
                except KeyError:
                    plugin_to_session_id[message['plugin']] = session_id = None

            if message['session_id'] != session_id:
                log.debug("Dropping message because it has stale session id (current is %s): %s" % (session_id, message))
                return False

            return True

        return [m for m in messages if is_valid(m)]

    @log_exception
    def get(self, request):
        """
        Send messages TO the agent.
        Handle a long-polling GET for messages to the agent
        """

        fqdn = self.valid_fqdn(request)
        if not fqdn:
            return HttpForbidden()
        server_boot_time = dateutil.parser.parse(request.GET['server_boot_time'])
        client_start_time = dateutil.parser.parse(request.GET['client_start_time'])

        messages = []

        try:
            reset_required = self.hosts.update(fqdn, server_boot_time, client_start_time)
        except ManagedHost.DoesNotExist:
            # This should not happen because the HTTPS frontend should have the
            # agent certificate revoked before removing the ManagedHost from the database
            log.error("GET from unknown server %s" % fqdn)
            return HttpResponseBadRequest("Unknown server '%s'" % fqdn)

        if reset_required:
            # This is the case where the http_agent service restarts, so
            # we have to let the agent know that all open sessions
            # are now over.
            messages.append({
                'fqdn': fqdn,
                'type': 'SESSION_TERMINATE_ALL',
                'plugin': None,
                'session_id': None,
                'session_seq': None,
                'body': None
            })

        log.debug("MessageView.get: composing messages for %s" % fqdn)
        queue = self.queues.get(fqdn).tx

        try:
            first_message = queue.get(block = True, timeout = self.LONG_POLL_TIMEOUT)
        except Queue.Empty:
            pass
        else:
            # TODO: limit number of messages per response
            messages.append(first_message)
            while True:
                try:
                    messages.append(queue.get(block = False))
                except Queue.Empty:
                    break

        messages = self._filter_valid_messages(fqdn, messages)

        log.debug("MessageView.get: responding to %s with %s messages" % (fqdn, len(messages)))
        return HttpResponse(json.dumps({'messages': messages}), mimetype = "application/json")


@csrf_exempt
@log_exception
def register(request, key):
    from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

    if request.method != "POST":
        return HttpResponseNotAllowed(['POST'])

    # Validate the secret key
    try:
        with transaction.commit_on_success():
            token = RegistrationToken.objects.get(secret = key)
            if not token.credits:
                log.warning("Attempt to register with exhausted token %s" % key)
                return HttpForbidden()
            else:
                # Decrement .credits
                RegistrationToken.objects.filter(secret = key).update(credits = token.credits - 1)
    except RegistrationToken.DoesNotExist:
        log.warning("Attempt to register with non-existent token %s" % key)
        return HttpForbidden()
    else:
        now = datetime.datetime.utcnow()
        now = now.replace(tzinfo = dateutil.tz.tzutc())

        if token.expiry < now:
            log.warning("Attempt to register with expired token %s (now %s, expired at %s)" % (key, now, token.expiry))
            return HttpForbidden()
        elif token.cancelled:
            log.warning("Attempt to register with cancelled token %s" % key)
            return HttpForbidden()

    host_attributes = json.loads(request.body)

    # Fail at the first if the version of the agent on the server is incorrect
    manager, agent = Version(settings.VERSION), Version(host_attributes['version'])
    if manager and agent and not (manager.major == agent.major and manager.minor >= agent.minor):
        return HttpResponse(status = 400, content = "Version incompatibility between manager {0} and agent {1}".format(manager, agent))

    # Fulfil the registering server's request for a certificate authenticating
    # it as the owner of this FQDN.
    csr = host_attributes['csr']

    # Check that the commonName in the CSR is the same as that in host_attributes
    # (prevent registering as one host and getting a certificate to impersonate another)
    csr_fqdn = Crypto().get_common_name(csr)
    if csr_fqdn != host_attributes['fqdn']:
        # Terse response to attacker
        log.error("FQDN mismatch '%s' vs. '%s' from %s" % (csr_fqdn, host_attributes['fqdn'], request.META['HTTP_X_FORWARDED_FOR']))
        return HttpResponse(status = 400, content = "")

    certificate_str = Crypto().sign(csr)
    certificate_serial = Crypto().get_serial(certificate_str)
    log.info("Generated certificate %s:%s" % (host_attributes['fqdn'], certificate_serial))
    MessageView.valid_certs[certificate_serial] = host_attributes['fqdn']

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

    host, command = JobSchedulerClient.create_host(
        address = host_attributes['address'],
        fqdn = host_attributes['fqdn'],
        nodename = host_attributes['nodename'],
        capabilities = host_attributes['capabilities']
    )

    with transaction.commit_on_success():
        ClientCertificate.objects.create(host = host, serial = certificate_serial)

    # TODO: document this return format
    return HttpResponse(status = 201, content = json.dumps({
        'command_id': command.id,
        'host_id': host.id,
        'certificate': certificate_str
    }), mimetype = "application/json")


@csrf_exempt
@log_exception
def reregister(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    fqdn = MessageView.valid_fqdn(request)
    if not fqdn:
        return HttpForbidden()
    host_attributes = json.loads(request.body)

    MessageView.valid_certs[request.META['HTTP_X_SSL_CLIENT_SERIAL']] = host_attributes['fqdn']
    ManagedHost.objects.filter(fqdn=fqdn).update(fqdn=host_attributes['fqdn'], address=host_attributes['address'])
    return HttpResponse()
