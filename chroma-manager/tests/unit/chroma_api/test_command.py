
from chroma_api.job import JobResource
from chroma_core.models.host import ManagedHost
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCaseHeavy


class TestCommandResource(ChromaApiTestCaseHeavy):
    def setUp(self):
        self.mock_servers = {}
        for n in range(0, 10):
            self.mock_servers["server%s" % n] = {
                'fqdn': 'server%s.mycompany.com' % n,
                'nodename': 'test%s.myaddress.mycompany.com' % n,
                'nids': ["192.168.0.%s@tcp0" % n]
            }
        super(TestCommandResource, self).setUp()

    def test_host_lists(self):
        """Test that commands which take a list of hosts as an argument
        are accepted correctly"""

        hosts = list(ManagedHost.objects.all())
        # An arbitrary subset of the hosts
        host_subset = [hosts[0], hosts[5]]

        from chroma_api.urls import api

        response = self.api_client.post("/api/command/", data = {
            'message': "Test command",
            'jobs': [
                    {
                    'class_name': 'RelearnNidsJob',
                    'args': {'hosts': [api.get_resource_uri(h) for h in host_subset]}
                }
            ]
        })
        self.assertEqual(response.status_code, 201)
        command = self.deserialize(response)
        jobs = [JobResource().get_via_uri(uri) for uri in command['jobs']]

        self.assertSetEqual(set(jobs[0].hosts.all()), set(host_subset))

    def test_absent_host_list(self):
        """Test that commands which take a list of hosts as an argument
        are accepted with no list of hosts and implicitly refer to all"""

        hosts = list(ManagedHost.objects.all())

        response = self.api_client.post("/api/command/", data = {
            'message': "Test command",
            'jobs': [
                    {
                    'class_name': 'RelearnNidsJob',
                    'args': {}
                }
            ]
        })
        self.assertEqual(response.status_code, 201)
        command = self.deserialize(response)
        jobs = [JobResource().get_via_uri(uri) for uri in command['jobs']]
        self.assertSetEqual(set(jobs[0].hosts.all()), set(hosts))
