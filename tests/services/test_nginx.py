"""
Tests for the frontend HTTP and HTTPS functionality provided by nginx
"""

import subprocess
import tempfile
import sys
import requests
import settings
import socket
import ssl
from tests.services.http_listener import HttpListener
from tests.services.systemd_test_case import SystemdTestCase


class NginxTestCase(SystemdTestCase):
    # Require job_scheduler because it is queried for available_transitions when rendering /ui/
    SERVICES = ["nginx", "emf-gunicorn", "emf-job-scheduler"]


class TestInsecureUrls(NginxTestCase):
    """
    Test the namespaces that do not require SSL client authentication
    """

    def test_http_redirect(self):
        """Test that connections on the HTTP scheme are redirected
        to the HTTPS url"""

        response = requests.get(
            "http://localhost:%s/" % settings.HTTPS_FRONTEND_PORT, verify=False, allow_redirects=False
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "https://localhost:%s/" % settings.HTTPS_FRONTEND_PORT)

    def test_missing_slash(self):
        """Test rewriting of HTTP redirects is happening (ProxyPassReverse)"""

        without_slash = "/api/session"
        response = requests.get("https://localhost{}".format(without_slash), verify=False, allow_redirects=False)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.headers["location"], without_slash + "/")

    def test_simple_access(self):
        """Test passthrough for /api/"""

        response = requests.get("https://localhost:%s/api/session/" % settings.HTTPS_FRONTEND_PORT, verify=False)
        self.assertEqual(response.status_code, 200)

    def test_register_access(self):
        """Test un-authenticated proxying for /agent/register/"""

        with HttpListener(settings.HTTP_AGENT_PORT) as listener:
            response = requests.post(
                "https://localhost:%s/agent/register/" % settings.HTTPS_FRONTEND_PORT, verify=False
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(listener.requests), 1)
            self.assertEqual(listener.last_request.path, "/agent/register/")

    def test_certificate(self):
        """Test certificate is fetchable"""
        with open("%s/authority.crt" % settings.SSL_PATH, "r") as cert:
            text = cert.read()
            response = requests.get("https://localhost:%s/certificate" % settings.HTTPS_FRONTEND_PORT, verify=False)
            self.assertEqual(response.text, text)

    def test_certificate_redirect(self):
        """Test certificate path redirects"""
        without_slash = "https://localhost:%s/certificate/" % settings.HTTPS_FRONTEND_PORT
        response = requests.get(without_slash, verify=False, allow_redirects=False)
        self.assertEqual(response.status_code, 301)


class TestSecureUrls(NginxTestCase):
    """
    Test the namespaces that require SSL client authentication
    """

    # Note that this test replicates a subset of the manager and agent Crypto classes, this
    # is intentional as the unit under test is the HTTPS frontend config, not those classes.
    def _openssl(self, args):
        p = subprocess.Popen(["openssl"] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        sys.stdout.write(stdout)
        sys.stdout.write(stderr)
        self.assertEqual(p.returncode, 0)
        return p.returncode, stdout, stderr

    def _bad_server_credentials(self):
        server_key = tempfile.NamedTemporaryFile(delete=False)
        server_cert = tempfile.NamedTemporaryFile(delete=False)
        csr = tempfile.NamedTemporaryFile()

        # A private key
        self._openssl(["genrsa", "-out", server_key.name, "2048"])
        # A self signed cert
        self._openssl(
            [
                "req",
                "-new",
                "-subj",
                "/C=/ST=/L=/O=/CN=x_local_authority",
                "-key",
                server_key.name,
                "-out",
                csr.name,
                "-sha256",
            ]
        )
        self._openssl(
            [
                "x509",
                "-req",
                "-days",
                "36500",
                "-signkey",
                server_key.name,
                "-out",
                server_cert.name,
                "-in",
                csr.name,
                "-sha256",
            ]
        )

        return server_key.name, server_cert.name

    def _client_credentials(self, client_cn, authority_key, authority_cert):
        client_key = tempfile.NamedTemporaryFile(delete=False)
        client_cert = tempfile.NamedTemporaryFile(delete=False)
        client_csr = tempfile.NamedTemporaryFile()

        # Client key
        self._openssl(["genrsa", "-out", client_key.name, "2048"])
        # Client CSR
        self._openssl(
            [
                "req",
                "-new",
                "-subj",
                "/C=/ST=/L=/O=/CN=%s" % client_cn,
                "-key",
                client_key.name,
                "-out",
                client_csr.name,
                "-sha256",
            ]
        )
        # Generate client cert
        self._openssl(
            [
                "x509",
                "-req",
                "-days",
                "36500",
                "-sha256",
                "-CAkey",
                authority_key,
                "-CA",
                authority_cert,
                "-CAcreateserial",
                "-out",
                client_cert.name,
                "-in",
                client_csr.name,
            ]
        )

        return client_cert.name, client_key.name

    def test_no_cert(self):
        """Check that I'm rejected if I try to connect to the secure namespace without a certificate"""
        with HttpListener(settings.HTTP_AGENT_PORT) as listener:
            # Check that we are rejected
            response = requests.post("https://localhost:%s/agent/message/" % settings.HTTPS_FRONTEND_PORT, verify=False)

            self.assertEqual(response.status_code, 401)

            # And that nothing was proxied to the agent service
            self.assertEqual(len(listener.requests), 0)

    def test_bad_cert(self):
        """Check that I'm bounced if I connect with a certificate from a different CA"""

        client_cn = "myserver"
        authority_key, authority_cert = self._bad_server_credentials()
        cert, key = self._client_credentials(client_cn, authority_key, authority_cert)

        with HttpListener(settings.HTTP_AGENT_PORT) as listener:
            # Check that we are rejected
            response = requests.get(
                "https://localhost:%s/agent/message/" % settings.HTTPS_FRONTEND_PORT, verify=False, cert=(cert, key)
            )

            self.assertEqual(response.status_code, 400)

            # And that nothing was proxied to the agent service
            self.assertEqual(len(listener.requests), 0)

    def test_good_cert(self):
        """Check that I'm allowed in with a valid certificate"""

        client_cn = "myserver"
        # FIXME: move these filenames out into settings.py (duplicated here from Crypto())
        authority_key = "{0}/authority.pem".format(settings.SSL_PATH)
        authority_cert = "{0}/authority.crt".format(settings.SSL_PATH)
        cert, key = self._client_credentials(client_cn, authority_key, authority_cert)

        rc, stdout, stderr = self._openssl(["x509", "-in", cert, "-serial", "-noout"])
        client_cert_serial = stdout.strip().split("=")[1]

        url = "https://localhost:%s/agent/message/" % settings.HTTPS_FRONTEND_PORT
        with HttpListener(settings.HTTP_AGENT_PORT) as listener:
            response = requests.post(url, data=" " * 16 * 1024, verify=False, cert=(cert, key))
            self.assertEqual(response.status_code, 200)
            response = requests.post(url, data=" " * 16 * 1024 ** 2, verify=False, cert=(cert, key))
            self.assertEqual(response.status_code, 413)
            response = requests.get(url, verify=False, cert=(cert, key))
            # My request succeeded
            self.assertEqual(response.status_code, 200)
            # A request was forwarded
            self.assertEqual(len(listener.requests), 2)
            self.assertEqual(listener.last_request.path, "/agent/message/")
            # The client name header was set
            self.assertEqual(listener.last_request.headers.getheader("X-SSL-Client-On"), "SUCCESS")
            self.assertEqual(listener.last_request.headers.getheader("X-SSL-Client-Name"), client_cn)
            self.assertEqual(listener.last_request.headers.getheader("X-SSL-Client-Serial"), client_cert_serial)

            url = "https://localhost:%s/agent/reregister/" % settings.HTTPS_FRONTEND_PORT
            response = requests.post(url, verify=False, cert=(cert, key))
            self.assertEqual(response.status_code, 200)


class TestCrypto(SystemdTestCase):
    SERVICES = ["nginx"]

    def _connect_socket(self, *args, **kwargs):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        ssl_sock = ssl.wrap_socket(sock, *args, **kwargs)

        ssl_sock.connect(("127.0.0.1", settings.HTTPS_FRONTEND_PORT))

        sock.close()

    """
    This test looks to see that SSLv3 is disabled this is needed due to the great POODLE scare of the summer
    of 2014.

    https://www.us-cert.gov/ncas/alerts/TA14-290A
    """

    def test_ssl3_disabled(self):
        self.assertRaises(socket.error, self._connect_socket, ssl_version=ssl.PROTOCOL_SSLv3)

    def test_ssl2_disabled(self):
        try:
            self.assertRaises(socket.error, self._connect_socket, ssl_version=ssl.PROTOCOL_SSLv2)
        except AttributeError:
            # RHEL 7.5 (for example)'s Python doesn't support
            # SSLv2 any more
            pass

    def test_tls1_disabled(self):
        self.assertRaises(socket.error, self._connect_socket, ssl_version=ssl.PROTOCOL_TLSv1)

    def test_tls1_1_disabled(self):
        self.assertRaises(socket.error, self._connect_socket, ssl_version=ssl.PROTOCOL_TLSv1_1)

    def test_tls1_2_enabled(self):
        self._connect_socket(ssl_version=ssl.PROTOCOL_TLSv1_2)

    def test_good_cipher(self):
        self._connect_socket(ssl_version=ssl.PROTOCOL_TLSv1_2, ciphers="ECDHE-RSA-AES128-GCM-SHA256")

    def test_bad_ciphers(self):
        bad_ciphers = ["DH+3DES", "ADH", "AECDH", "RC4", "aNULL", "MD5"]

        for bad_cipher in bad_ciphers:
            self.assertRaises(socket.error, self._connect_socket, ssl_version=ssl.PROTOCOL_TLSv1_2, ciphers=bad_cipher)

    def test_connection(self):
        self._connect_socket()
