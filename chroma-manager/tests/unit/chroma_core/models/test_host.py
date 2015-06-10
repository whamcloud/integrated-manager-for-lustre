
import json
from django.test import TestCase
from django.db import connection

from chroma_core.models.host import HostListMixin, ManagedHost


class TestHostListMixin(TestCase):
    def setUp(self):
        connection.use_debug_cursor = True

        self.hosts = []
        for i in range(0, 2):
            address = "myserver_%d" % i
            self.hosts.append(ManagedHost.objects.create(
                address = address,
                fqdn = address,
                nodename = address
            ))

    def tearDown(self):
        connection.use_debug_cursor = False

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

        db_hits = len(connection.queries)
        self.assertListEqual(instance.hosts, [self.hosts[1]])
        self.assertEqual(db_hits, len(connection.queries))

    def test_changing_hosts(self):
        instance = HostListMixin()
        instance.host_ids = json.dumps([self.hosts[1].id])
        self.assertListEqual(instance.hosts, [self.hosts[1]])

        db_hits = len(connection.queries)
        instance.host_ids = json.dumps([self.hosts[0].id])
        self.assertListEqual(instance.hosts, [self.hosts[0]])
        self.assertNotEqual(db_hits, len(connection.queries))
