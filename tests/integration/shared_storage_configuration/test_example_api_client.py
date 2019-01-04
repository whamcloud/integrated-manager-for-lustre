import socket
import urlparse
from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.shared_storage_configuration import example_api_client


class TestExampleApiClient(ChromaIntegrationTestCase):
    def test_login(self):
        self.hosts = self.add_hosts([config["lustre_servers"][0]["address"], config["lustre_servers"][1]["address"]])

        # Chroma puts its FQDN in the manager certificate, but the test config may
        # be pointing to localhost: if this is the case, substitute the FQDN in the
        # URL so that the client can validate the certificate.
        url = config["chroma_managers"][0]["server_http_url"]
        parsed = urlparse.urlparse(url)
        if parsed.hostname == "localhost":
            parsed = list(parsed)
            parsed[1] = parsed[1].replace("localhost", socket.getfqdn())
            url = urlparse.urlunparse(tuple(parsed))

        example_api_client.setup_ca(url)
        hosts = example_api_client.list_hosts(
            url,
            config["chroma_managers"][0]["users"][0]["username"],
            config["chroma_managers"][0]["users"][0]["password"],
        )
        self.assertListEqual(hosts, [h["fqdn"] for h in self.hosts])
