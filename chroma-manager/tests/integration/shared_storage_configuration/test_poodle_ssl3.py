import socket
import ssl

from django.utils import unittest

from testconfig import config

from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


@unittest.skipIf(config.get('simulator', False), "Poodle SSLv3 tests can't be simulated")
class TestPoodleSSLv3(ChromaIntegrationTestCase):
    '''
    This test looks to see that SSLv3 is disabled this is needed due to the great POODLE scare of the summer
    of 2014.

    https://www.us-cert.gov/ncas/alerts/TA14-290A
    '''
    def test_ssl3_disabled(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        ssl_sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv3)

        self.assertRaises(ssl.SSLError,
                          ssl_sock.connect,
                          ((config['chroma_managers'][0]['fqdn'], 443)))

    def test_ssl2_disabled(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        ssl_sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv2)

        self.assertRaises(ssl.SSLError,
                          ssl_sock.connect,
                          ((config['chroma_managers'][0]['fqdn'], 443)))

    def test_tls1_enabled(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        ssl_sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1)

        ssl_sock.connect((config['chroma_managers'][0]['fqdn'], 443))

        sock.close()

    def test_connection(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        ssl_sock = ssl.wrap_socket(sock)

        ssl_sock.connect((config['chroma_managers'][0]['fqdn'], 443))

        sock.close()
