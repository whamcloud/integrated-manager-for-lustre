# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from networkx import Graph, find_cliques
from chroma_core.models.host import ManagedHost


class HaCluster(object):
    @classmethod
    def all_clusters(cls):
        graph = Graph()
        for edges in [[(h, p) for p in h.ha_cluster_peers.all()] for h in ManagedHost.objects.all()]:
            graph.add_edges_from(edges)

        clusters = []
        for cluster_peers in find_cliques(graph):
            clusters.append(cls(cluster_peers))
        return clusters

    @classmethod
    def host_peers(cls, host):
        for clusters in cls.all_clusters():
            if host in clusters.peers:
                return clusters.peers

        return []

    def __init__(self, peer_list):
        self.peer_list = peer_list

    @property
    def peers(self):
        return self.peer_list
