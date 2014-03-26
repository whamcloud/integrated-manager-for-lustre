#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


from chroma_core.lib.storage_plugin.api import attributes, statistics
from chroma_core.lib.storage_plugin.api.identifiers import ScopedId
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api.plugin import Plugin

# This plugin is special, it uses chroma-manager internals
# in a way that third party plugins can't/shouldn't/mustn't
#from chroma_core.lib.storage_plugin.base_resource import HostsideResource
#from chroma_core.models import ManagedHost

version = 1


# This is not used anymore it is here purely to satisfy the upgrade requirements of IML.
class NetworkInterface(resources.Resource):
    class Meta:
        identifier = ScopedId('name')
        charts = [{"title": "Bandwidth", "series": ['rx_bytes', 'tx_bytes']}]

    name = attributes.String()
    rx_bytes = statistics.Counter(units = "Bytes/s")
    tx_bytes = statistics.Counter(units = "Bytes/s")


class HostNetworkInterface(resources.NetworkInterface):
    """Used for marking devices which are already in use, so that
    we don't offer them for use as Lustre targets."""
    class Meta:
        identifier = ScopedId('host_id', 'name')

    name = attributes.String()
    inet4_address = attributes.String()
    type = attributes.String()
    up = attributes.Boolean()

    rx_bytes = statistics.Counter(units = "Bytes/s")
    tx_bytes = statistics.Counter(units = "Bytes/s")


class Nid(resources.LNETInterface):
    class Meta:
        identifier = ScopedId('host_id', 'name')

    """Simplified NID representation for those we detect already-configured"""
    name = attributes.String()                  # This is only used to scope it.
    host_id = attributes.Integer()              # Need so we uniquely identify it.
    lnd_network = attributes.Integer()


class LNetState(resources.LNETModules):
    class Meta:
        identifier = ScopedId('host_id')

    """ Lnet is pretty simple at the moment just a state """
    state = attributes.String()


class LinuxNetwork(Plugin):
    internal = True

    def agent_session_continue(self, host_resource, data):
        self.agent_session_start(host_resource, data)

    def agent_session_start(self, host_id, data):
        try:
            devices = data

            for expected_item in ['interfaces', 'lnet']:
                if expected_item not in devices:
                    raise RuntimeError("LinuxNetwork expected but didn't find %s" % expected_item)

            inet4_address_to_interface = {}

            ''' Actually I think this deleted here is unnecessary, it is probably the case that this routine
                could audit each nid against each network interface and work out which ones are now missing
                but this needs to land and this does work.
                But it any real work happens on this code, this should be removed.
            '''
            for name in devices['interfaces']['deleted']:
                self.remove_by_attr(HostNetworkInterface,
                                    host_id = host_id,
                                    name = name)

            for name, iface in devices['interfaces']['active'].iteritems():
                iface_resource, created = self.update_or_create(HostNetworkInterface,
                                                                name = name,
                                                                inet4_address = iface['inet4_address'],
                                                                host_id = host_id,
                                                                type = iface['type'],
                                                                up = iface['up'])

                iface_resource.rx_bytes = iface['rx_bytes']
                iface_resource.tx_bytes = iface['tx_bytes']

                inet4_address_to_interface[iface_resource.name] = iface_resource

            ''' Actually I think this deleted here is unnecessary, it is probably the case that this routine
                could audit each nid against each network interface and work out which ones are now missing
                but this needs to land and this does work.
                But it any real work happens on this code, this should be removed.
            '''
            for name in devices['lnet']['nids']['deleted']:
                self.remove_by_attr(Nid,
                                    host_id = host_id,
                                    name = name)

            for name, nid in devices['lnet']['nids']['active'].iteritems():
                parent_interface = inet4_address_to_interface[name]

                assert(name == parent_interface.name)

                db_nid, created = self.update_or_create(Nid,
                                                        parents = [parent_interface],
                                                        name = name,
                                                        host_id = host_id,
                                                        lnd_network = nid['lnd_network'])

                if created:
                    self.log.debug("Learned new nid %s:%s@%s%s" % (parent_interface.host_id, parent_interface.inet4_address, parent_interface.type, nid['lnd_network']))

            lnet_state, created = self.update_or_create(LNetState,
                                                        host_id = host_id,
                                                        state = devices['lnet']['state'])
            if created:
                self.log.debug("Learned new lnet modules on %s" % host_id)

        except Exception:
            pass
