import json

from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests.unit.lib.emf_unit_test_case import EMFUnitTestCase

from chroma_core.models.host import HostListMixin, ManagedHost


class TestHostListMixin(EMFUnitTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hosts = []

        for i in range(0, 2):
            address = "myserver_%d" % i
            h = ManagedHost.objects.create(address=address, fqdn=address, nodename=address)

            cls.hosts.append(h)

    def setUp(self):
        super(TestHostListMixin, self).setUp()

        for h in self.hosts:
            h.refresh_from_db()

    def test_all_hosts(self):
        """When given no host IDs, default to all hosts"""
        instance = HostListMixin()
        instance.host_ids = ""
        self.assertListEqual(instance.hosts, self.hosts)

    def test_selective_hosts(self):
        instance = HostListMixin()
        instance.host_ids = json.dumps([self.hosts[1].id])
        self.assertListEqual(instance.hosts, [self.hosts[1]])

    def test_cached_hosts(self):
        instance = HostListMixin()
        instance.host_ids = json.dumps([self.hosts[1].id])
        self.assertListEqual(instance.hosts, [self.hosts[1]])

        with self.assertNumQueries(0):
            self.assertListEqual(instance.hosts, [self.hosts[1]])

    def test_changing_hosts(self):
        instance = HostListMixin()
        instance.host_ids = json.dumps([self.hosts[1].id])

        with self.assertNumQueries(1):
            self.assertListEqual(instance.hosts, [self.hosts[1]])

        instance.host_ids = json.dumps([self.hosts[0].id])

        with self.assertNumQueries(1):
            self.assertListEqual(instance.hosts, [self.hosts[0]])
