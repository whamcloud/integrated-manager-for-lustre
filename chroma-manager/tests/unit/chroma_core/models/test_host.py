
import json
from django.test import TestCase
from chroma_core.models.host import HostListMixin, ManagedHost


class TestHostListMixin(TestCase):
    def setUp(self):
        self.hosts = []
        for i in range(0, 2):
            address = "myserver_%d" % i
            self.hosts.append(ManagedHost.objects.create(
                address = address,
                fqdn = address,
                nodename = address
            ))

    def test_all_hosts(self):
        """When given no host IDs, default to all hosts"""
        instance = HostListMixin()
        instance.host_ids = ""
        self.assertListEqual(list(instance.hosts.all()), self.hosts)

    def test_selective_hosts(self):
        instance = HostListMixin()
        instance.host_ids = json.dumps([self.hosts[1].id])
        self.assertListEqual(list(instance.hosts.all()), [self.hosts[1]])
