#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from networkx import Graph, find_cliques
from chroma_core.models.host import ManagedHost


class HaCluster(object):
    @classmethod
    def all_clusters(cls):
        graph = Graph()
        for edges in [[(h, p) for p in h.ha_cluster_peers.all()]
                                    for h in ManagedHost.objects.all()]:
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
