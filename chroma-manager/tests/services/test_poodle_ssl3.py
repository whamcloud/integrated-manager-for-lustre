import socket
import ssl

from tests.services.supervisor_test_case import SupervisorTestCase


class TestPoodleSSLv3(SupervisorTestCase):
    SERVICES = ['nginx']

    """
    This test looks to see that SSLv3 is disabled this is needed due to the great POODLE scare of the summer
    of 2014.

    https://www.us-cert.gov/ncas/alerts/TA14-290A
    """
    def test_ssl3_disabled(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        ssl_sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv3)

        self.assertRaises(ssl.SSLError,
                          ssl_sock.connect,
                          ('127.0.0.1', 8000))

    def test_ssl2_disabled(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        ssl_sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv2)

        self.assertRaises(socket.error,
                          ssl_sock.connect,
                          ('127.0.0.1', 8000))

    def test_tls1_enabled(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        ssl_sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1)

        ssl_sock.connect(('127.0.0.1', 8000))

        sock.close()

    def test_connection(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        ssl_sock = ssl.wrap_socket(sock)

        ssl_sock.connect(('127.0.0.1', 8000))

        sock.close()
