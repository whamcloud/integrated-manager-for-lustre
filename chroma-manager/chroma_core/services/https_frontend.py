#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import ssl
import urlparse
import wsgiref.util
import M2Crypto
from chroma_core.lib.util import CommandLine
from chroma_core.models import ManagedHost
from chroma_core.services import ChromaService, log_register, ServiceThread
from chroma_core.services.rpc import ServiceRpcInterface
import gevent.pywsgi
import os
from settings import HTTP_AGENT_PORT, HTTP_API_PORT, HTTPS_FRONTEND_PORT
import settings
from wsgiproxy.app import WSGIProxyApp


security_log = log_register('security')


class RoutingProxyRpc(ServiceRpcInterface):
    methods = ['revoke']


class RoutingProxy(object):
    """
    This class is the first code that touches incoming HTTPS requests.  It is responsible for:
     * Enforcing client SSL certificate security
     * Adding the HTTP_X_IMFL_FQDN header where appropriate
     * Proxying requests onwards to the appropriate service for the URL
    """
    DEFAULT_PATH = "ui/"
    SECURE_FQDN_HEADER = 'HTTP_X_IMFL_FQDN'

    def __init__(self, log):
        self._api_proxy = WSGIProxyApp("http://localhost:%s/" % HTTP_API_PORT)
        self._agent_proxy = WSGIProxyApp("http://localhost:%s/" % HTTP_AGENT_PORT)
        self._log = log
        self._revoked_fingerprints = set([mh['ssl_fingerprint'] for mh in ManagedHost._base_manager.filter(not_deleted = None).values('ssl_fingerprint')])

    def revoke(self, ssl_fingerprint):
        self._revoked_fingerprints.add(ssl_fingerprint)

    def _simple_response(self, start_response, status_code, text, headers = list()):
        from django.core.handlers.wsgi import STATUS_CODE_TEXT
        start_response("%s %s" % (status_code, STATUS_CODE_TEXT[status_code]), [('Content-type', 'text/plain')] + headers)
        yield text

    def __call__(self, environ, start_response):
        ssl_socket = environ['wsgi.input'].ssl_socket
        validated_client_cert = ssl_socket.getpeercert()
        if self.SECURE_FQDN_HEADER in environ:
            # This is an attack, so be tight lipped
            security_log.warning("SECURE_FQDN_HEADER already set to '%s' from %s" % (environ[self.SECURE_FQDN_HEADER], environ['REMOTE_ADDR']))
            return self._simple_response(start_response, 400, "")

        raw_client_cert = ssl_socket.getpeercert(binary_form = True)
        if raw_client_cert:
            if not validated_client_cert:
                # An invalid certificate was submitted
                security_log.warning("Invalid client certificate from %s: %s" % (environ['REMOTE_ADRR'], raw_client_cert))
                return self._simple_response(start_response, 403, "")
            else:
                client_cert_fingerprint = M2Crypto.X509.load_cert_string(raw_client_cert, format = M2Crypto.X509.FORMAT_DER)
                if client_cert_fingerprint in self._revoked_fingerprints:
                    security_log.warning("Revoked client certificate from %s: %s" % (environ['REMOTE_ADRR'], raw_client_cert))
                    return self._simple_response(start_response, 403, "")

        if validated_client_cert:
            # Set HTTP_X_IMFL_FQDN based on the client certificate
            fqdn = None
            for rdn in validated_client_cert['subject']:
                for k, v in rdn:
                    if k == 'commonName':
                        fqdn = v
                        break
                if fqdn:
                    break

            if fqdn is None:
                security_log.warning("Invalid client cert (no FQDN) from %s: %s" % (environ['REMOTE_ADRR'], raw_client_cert))
                return self._simple_response(start_response, 400, "SSL client certificate lacks commonName")
            else:
                environ[self.SECURE_FQDN_HEADER] = fqdn

        path = urlparse.urlparse(environ['PATH_INFO']).path
        if path == "/":
            uri = wsgiref.util.application_uri(environ) + self.DEFAULT_PATH
            return self._simple_response(start_response, 301, "", [('Location', uri)])
        elif path.startswith("/api/") or path.startswith("/ui/") or path.startswith('/static/'):
            return self._api_proxy(environ, start_response)
        elif path.startswith("/certificate/"):
            # We could serve this from the API, but it doesn't fit in naturally anywhere, and
            # the file kind of 'lives' at this level
            return self._simple_response(start_response, 200, open(Crypto().authority_cert).read().strip(), [('Content-Disposition', 'attachment; filename="chroma.ca"')])
        elif path.startswith("/agent/register/"):
            return self._agent_proxy(environ, start_response)
        elif path.startswith("/agent/message/"):
            # Agent messaging must have an SSL client certificate
            if not validated_client_cert:
                return self._simple_response(start_response, 403, "SSL client certificate required")
            else:
                return self._agent_proxy(environ, start_response)
        else:
            security_log.warning("Request for bad path '%s' from %s" % (path, environ['REMOTE_ADDR']))
            return self._simple_response(start_response, 404, "Unknown path")


class Crypto(CommandLine):
    # The manager's local key and certificate, used for
    # identifying itself to agents and to API clients such
    # as web browsers and the command line interface.
    MANAGER_KEY_FILE = 'privkey.pem'
    MANAGER_CERT_FILE = 'manager.crt'

    # The local CA used for issuing certificates to agents, and
    # for signing the manager cert if an externally signed cert
    # is not provided
    AUTHORITY_KEY_FILE = 'authority.pem'
    AUTHORITY_CERT_FILE = 'authority.crt'

    log = log_register('crypto')

    # FIXME: set durations when signing to something meaningful (permanent?)

    def _get_or_create_private_key(self, filename):
        if not os.path.exists(filename):
            self.log.info("Generating manager key file")
            self.try_shell(['openssl', 'genrsa', '-out', filename, '2048'])
        return filename

    @property
    def authority_key(self):
        """
        Get the path to the authority key, or generate one
        """
        return self._get_or_create_private_key(self.AUTHORITY_KEY_FILE)

    @property
    def authority_cert(self):
        """
        Get the path to the authority certificate, or self-sign the authority key to generate one
        """
        if not os.path.exists(self.AUTHORITY_CERT_FILE):
            rc, csr, err = self.try_shell(["openssl", "req", "-new", "-subj", "/C=/ST=/L=/O=/CN=x_local_authority", "-key", self.authority_key])
            rc, out, err = self.try_shell(["openssl", "x509", "-req", "-days", "365", "-signkey", self.authority_key, "-out", self.AUTHORITY_CERT_FILE], stdin_text = csr)

        return self.AUTHORITY_CERT_FILE

    @property
    def server_key(self):
        return self._get_or_create_private_key(self.MANAGER_KEY_FILE)

    @property
    def server_cert(self):
        if not os.path.exists(self.MANAGER_CERT_FILE):
            # Determine what domain name HTTP clients will
            # be using to access me, and bake that into my
            # certificate (using SERVER_HTTP_URL re
            hostname = urlparse.urlparse(settings.SERVER_HTTP_URL).hostname

            self.log.info("Generating manager certificate file")
            rc, csr, err = self.try_shell(["openssl", "req", "-new", "-subj", "/C=/ST=/L=/O=/CN=%s" % hostname, "-key", self.MANAGER_KEY_FILE])
            rc, out, err = self.try_shell(["openssl", "x509", "-req", "-days", "365", "-CA", self.authority_cert, "-CAcreateserial", "-CAkey", self.authority_key, "-out", self.MANAGER_CERT_FILE], stdin_text = csr)

            self.log.info("Generated %s" % self.MANAGER_CERT_FILE)
        return self.MANAGER_CERT_FILE

    def sign(self, csr_string):
        self.log.info("Signing")

        rc, out, err = self.try_shell(["openssl", "x509", "-req", "-days", "365", "-CAkey", self.authority_key, "-CA", self.authority_cert, "-CAcreateserial"], stdin_text = csr_string)
        return out.strip()


class SSLWSGIHandler(gevent.pywsgi.WSGIHandler):
    """
    The gevent WSGI handler works like:
    WSGIServer -> WSGIHandler -> Input
    when WSGIHandler constructs Input, it only passes along
    the socket if doing 100-continue stuff.
    So we use a minimally modified version that preserves a reference
    to the SSLSocket in the environment.
    """
    def get_environ(self):
        env = super(SSLWSGIHandler, self).get_environ()
        input = env['wsgi.input']
        input.ssl_socket = self.socket
        return env


class SSLWSGIServer(gevent.pywsgi.WSGIServer):
    handler_class = SSLWSGIHandler


# TODO: add a handler on port 80 that redirects to port 443
# (in production mode only)

# TODO: publish an RPC interface for other services to do certificate revocation
# (calling revoke on RoutingProxy)

class Service(ChromaService):
    def run(self):
        crypto = Crypto()
        proxy_app = RoutingProxy(self.log)

        rpc_thread = ServiceThread(RoutingProxyRpc(proxy_app))
        rpc_thread.start()

        # FIXME: shit, using CERT_OPTIONAL causes chrome to prompt the
        # browser user to use a client certificate: we will have to use
        # CERT_NONE+renegotiation

        # Apache knows how to do this, and can apply an SSLVerifyClient option
        # on a per-directory basis... are we actually doing anything here
        # that we couldn't delegate to apache?

        # TODO: it would be preferable to restrict the version of SSL in use
        # (to TLS) but leaving it open makes writing clients simpler

        self.log.info("Starting on port %s with key, cert = %s, %s" % (HTTPS_FRONTEND_PORT, crypto.server_key, crypto.server_cert))
        self.server = SSLWSGIServer(
            ('', HTTPS_FRONTEND_PORT),
            proxy_app,
            cert_reqs = ssl.CERT_OPTIONAL,
            keyfile = crypto.server_key,
            certfile = crypto.server_cert,
            ca_certs = crypto.authority_cert
        )
        self.server.serve_forever()

        rpc_thread.stop()
        rpc_thread.join()

    def stop(self):
        self.server.stop()
