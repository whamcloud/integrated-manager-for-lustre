from collections import defaultdict

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class ChromaHaTestCase(ChromaIntegrationTestCase):
    def setUp(self):
        super(ChromaHaTestCase, self).setUp()

        self.add_hosts([s['address'] for s in config['lustre_servers']])

        def _all_servers_up(testcase):
            servers = testcase.get_list("/api/host/")
            return all([server['corosync_reported_up'] for server in servers])

        self.wait_until_true(lambda: _all_servers_up(self))


class TestHaClusters(ChromaHaTestCase):
    def test_ha_cluster_count(self):
        # Adjust this if we ever support more.
        SERVERS_PER_HA_CLUSTER = 2

        clusters = self.get_list("/api/ha_cluster/")
        server_count = len(config['lustre_servers'])

        if server_count >= (SERVERS_PER_HA_CLUSTER * 2):
            # If we have at least 4 servers, then we should have at least
            # 2 HA clusters, assuming 2 servers per HA cluster.
            self.assertEqual(len(clusters), server_count / SERVERS_PER_HA_CLUSTER)
        elif server_count > (SERVERS_PER_HA_CLUSTER - 1):
            # Conversely, if we have fewer than 4 servers, but more than 1,
            # we should have exactly 1 cluster (2 peers + 1 not in a cluster).
            self.assertEqual(len(clusters), 1)

    def test_ha_clusters_are_distinct(self):
        # Verify that each host only appears in a single HA cluster.
        # Stupid brute-force test... Don't want to use a graph
        # analysis library to verify its own results.
        clusters = [[h['fqdn'] for h in c['peers']]
                        for c in self.get_list("/api/ha_cluster/")]
        for i, cluster in enumerate(clusters):
            for peer in cluster:
                for j, other_cluster in enumerate(clusters):
                    if i == j:
                        continue
                    self.assertNotIn(peer, other_cluster)


class TestHaClusterVolumes(ChromaHaTestCase):
    # FIXME: We don't currently have any audit logic which looks for
    # perfect storage meshing among HA peers -- but we probably should!
    #def test_clusters_with_imperfect_storage_mesh_raise_alerts(self):
    #    pass

    def test_api_rejects_multi_cluster_failover(self):
        # Make sure that we can't accidentally or otherwise set up
        # a primary/failover relationship across two HA clusters.
        clusters = self.get_list("/api/ha_cluster/")
        cluster_0_host = clusters[0]['peers'][0]
        cluster_1_host = clusters[1]['peers'][0]
        test_volume = self.get_list("/api/volume/")[0]
        payload = {'id': test_volume['id'], 'nodes': []}
        for vn in test_volume['volume_nodes']:
            if str(vn['host_id']) == str(cluster_0_host['id']):
                payload['nodes'].append({
                    'id': vn['id'],
                    'primary': True,
                    'use': True
                })
            elif str(vn['host_id']) == str(cluster_1_host['id']):
                payload['nodes'].append({
                    'id': vn['id'],
                    'primary': False,
                    'use': True
                })

        self.assertEqual(len(payload['nodes']), 2)
        response = self.chroma_manager.put(test_volume['resource_uri'],
                                           body = payload)
        self.assertEqual(response.status_code, 400, response.text)

    def test_volumes_assigned_to_single_clusters(self):
        # A given volume should only be usable with nodes in a single HA
        # cluster. Allowing fully-meshed volumes to be usable across
        # multiple HA clusters will lead to weird and broken behavior
        # (can't fail between different corosync clusters!).
        clusters = [[h['resource_uri'] for h in c['peers']]
                        for c in self.get_list("/api/ha_cluster/")]

        ha_volumes = set()
        ha_volume_cluster_hosts = defaultdict(list)
        volumes_usable_in_clusters = defaultdict(set)
        for volume in self.get_usable_volumes():
            if len(volume['volume_nodes']) > 0:
                ha_volumes.add(volume['label'])

            for volume_node in volume['volume_nodes']:
                for i, cluster in enumerate(clusters):
                    if volume_node['host'] in cluster and volume_node['use']:
                        ha_volume_cluster_hosts[volume['label']].append(volume_node['host'])
                        volumes_usable_in_clusters[volume['label']].add(str(i))

        errors = []
        for volume, vn_clusters in volumes_usable_in_clusters.items():
            if len(vn_clusters) > 1:
                errors.append("%s usable in multiple clusters: %s" % (volume, ", ".join(vn_clusters)))
            elif len(vn_clusters) < 1:
                errors.append("%s not usable in any clusters" % volume)

        for volume in ha_volumes:
            if len(ha_volume_cluster_hosts[volume]) < 2:
                errors.append("%s is usable on < 2 hosts, but should be HA-capable" % volume)

        self.assertEqual([], errors)
