
"""
Tests for the frontend HTTP and HTTPS functionality provided by Apache (httpd)
"""

import subprocess
import tempfile
import requests
from requests.exceptions import SSLError
import settings
from tests.services.http_listener import HttpListener
from tests.services.supervisor_test_case import SupervisorTestCase


class TestInsecureUrls(SupervisorTestCase):
    """
    Test the namespaces that do not require SSL client authentication
    """
    SERVICES = ['httpd']

    def test_http_redirect(self):
        """Test that connections on the HTTP url are redirected
           to the HTTPS url"""

        response = requests.get("http://localhost:%s/" % settings.HTTP_FRONTEND_PORT,
            verify = False, allow_redirects = False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['location'], "https://localhost:%s/" % settings.HTTPS_FRONTEND_PORT)

    def test_simple_access(self):
        """Test passthrough for /ui/, /api/, /static/"""

        response = requests.get("https://localhost:%s/ui/" % settings.HTTPS_FRONTEND_PORT, verify = False)
        self.assertEqual(response.status_code, 200)

        response = requests.get("https://localhost:%s/static/images/logo.png" % settings.HTTPS_FRONTEND_PORT, verify = False)
        self.assertEqual(response.status_code, 200)

        response = requests.get("https://localhost:%s/api/session/" % settings.HTTPS_FRONTEND_PORT, verify = False)
        self.assertEqual(response.status_code, 200)

    def test_register_access(self):
        """Test un-authenticated proxying for /agent/register/"""

        with HttpListener(settings.HTTP_AGENT_PORT) as listener:
            response = requests.post(
                "https://localhost:%s/agent/register/" % settings.HTTPS_FRONTEND_PORT,
                verify = False)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(listener.requests), 1)
            self.assertEqual(listener.last_request.path, "/agent/register/")


class TestSecureUrls(SupervisorTestCase):
    """
    Test the namespaces that require SSL client authentication
    """

    SERVICES = ['httpd']

    # Note that this test replicates a subset of the manager and agent Crypto classes, this
    # is intentional as the unit under test is the HTTPS frontend config, not those classes.
    def _openssl(self, args):
        rc = subprocess.call(['openssl'] + args)
        self.assertEqual(rc, 0)

    def _bad_server_credentials(self):
        server_key = tempfile.NamedTemporaryFile(delete = False)
        server_cert = tempfile.NamedTemporaryFile(delete = False)
        csr = tempfile.NamedTemporaryFile()

        # A private key
        self._openssl(['genrsa', '-out', server_key.name, '2048'])
        # A self signed cert
        self._openssl(["req", "-new", "-subj", "/C=/ST=/L=/O=/CN=x_local_authority", "-key", server_key.name, "-out", csr.name])
        self._openssl(["x509", "-req", "-days", "365", "-signkey", server_key.name, "-out", server_cert.name, "-in", csr.name])

        return server_key.name, server_cert.name

    def _client_credentials(self, client_cn, authority_key, authority_cert):
        client_key = tempfile.NamedTemporaryFile(delete = False)
        client_cert = tempfile.NamedTemporaryFile(delete = False)
        client_csr = tempfile.NamedTemporaryFile()

        # Client key
        self._openssl(['genrsa', '-out', client_key.name, '2048'])
        # Client CSR
        self._openssl(["req", "-new", "-subj", "/C=/ST=/L=/O=/CN=%s" % client_cn, "-key", client_key.name, "-out", client_csr.name])
        # Generate client cert
        self._openssl(["x509", "-req", "-days", "365", "-CAkey", authority_key, "-CA", authority_cert, "-CAcreateserial", "-out", client_cert.name, "-in", client_csr.name])

        return client_cert.name, client_key.name

    def test_no_cert(self):
        """Check that I'm rejected if I try to connect to the secure namespace without a certificate"""
        with HttpListener(settings.HTTP_AGENT_PORT) as listener:
            # Check that we are rejected
            with self.assertRaises(SSLError):
                requests.post(
                    "https://localhost:%s/agent/message/" % settings.HTTPS_FRONTEND_PORT,
                    verify = False)

            # And that nothing was proxied to the agent service
            self.assertEqual(len(listener.requests), 0)

    def test_bad_cert(self):
        """Check that I'm bounced if I connect with a certificate from a different CA"""

        client_cn = "myserver"
        authority_key, authority_cert = self._bad_server_credentials()
        cert, key = self._client_credentials(client_cn, authority_key, authority_cert)

        with HttpListener(settings.HTTP_AGENT_PORT) as listener:
            # Check that we are rejected
            with self.assertRaises(SSLError):
                requests.get(
                    "https://localhost:%s/agent/message/" % settings.HTTPS_FRONTEND_PORT,
                    verify = False,
                    cert = (cert, key))

            # And that nothing was proxied to the agent service
            self.assertEqual(len(listener.requests), 0)

    def test_revoked_cert(self):
        """Check that I'm bounced if my certificate is revoked"""
        # TODO
        pass

    def test_good_cert(self):
        """Check that I'm allowed in with a valid certificate"""

        client_cn = "myserver"
        # FIXME: move these filenames out into settings.py (duplicated here from Crypto())
        authority_key = "authority.pem"
        authority_cert = "authority.crt"
        cert, key = self._client_credentials(client_cn, authority_key, authority_cert)

        with HttpListener(settings.HTTP_AGENT_PORT) as listener:
            response = requests.get(
                "https://localhost:%s/agent/message/" % settings.HTTPS_FRONTEND_PORT,
                verify = False,
                cert = (cert, key))
            # My request succeeded
            self.assertEqual(response.status_code, 200)
            # A request was forwarded
            self.assertEqual(len(listener.requests), 1)
            self.assertEqual(listener.last_request.path, "/agent/message/")
            # The client name header was set
            self.assertEqual(listener.last_request.headers.getheader('X-SSL-Client-Name'), client_cn)
