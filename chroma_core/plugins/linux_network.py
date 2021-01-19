# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.lib.storage_plugin.api import attributes
from chroma_core.lib.storage_plugin.api.identifiers import ScopedId
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api.plugin import Plugin

from chroma_core.models import LNetConfiguration

# This plugin is special, it uses chroma-manager internals
# in a way that third party plugins can't/shouldn't/mustn't
# from chroma_core.lib.storage_plugin.base_resource import HostsideResource
# from chroma_core.models import ManagedHost

version = 1


# This is not used anymore it is here purely to satisfy the upgrade requirements of EMF.
class NetworkInterface(resources.Resource):
    class Meta:
        identifier = ScopedId("name")

    name = attributes.String()


class HostNetworkInterface(resources.NetworkInterface):
    """Used for marking devices which are already in use, so that
    we don't offer them for use as Lustre targets."""

    class Meta:
        identifier = ScopedId("host_id", "name")

    name = attributes.String()
    inet4_address = attributes.String()
    inet4_prefix = attributes.Integer(default=0)
    type = attributes.String()
    up = attributes.Boolean()


class Nid(resources.LNETInterface):
    class Meta:
        identifier = ScopedId("host_id", "name")

    # Simplified NID representation for those we detect already-configured
    name = attributes.String()  # This is only used to scope it.
    host_id = attributes.Integer()  # Need so we uniquely identify it.
    lnd_network = attributes.Integer()
    lnd_type = attributes.String(
        default=lambda storage_dict: "o2ib" if storage_dict["lnd_network"] == "o2ib" else "tcp"
    )


class LNetState(resources.LNETModules):
    class Meta:
        identifier = ScopedId("host_id")

    # Lnet is pretty simple at the moment just a state
    state = attributes.String()


class LinuxNetwork(Plugin):
    internal = True

    def __init__(self, resource_manager, scannable_id=None):

        # For the linux network we want all the info each time until the lnet is not unconfigured. This means we still
        # get given the state changes once we go into 'monitoring' mode.
        # We actually need to not calculate delta until the message that arrives after the first case where we
        # have gone to the lnet configurated state. So like the Two Ronnies sketch we have to answer the question
        # before last https://www.youtube.com/watch?v=y0C59pI_ypQ
        self._calc_changes_delta_next = False

        super(LinuxNetwork, self).__init__(resource_manager, scannable_id)

    def agent_session_continue(self, host_resource, devices):
        self.agent_session_start(host_resource, devices)

    def agent_session_start(self, host_id, devices):
        self._calc_changes_delta = self._calc_changes_delta_next
        self._calc_changes_delta_next = (
            LNetConfiguration.objects.get(host_id=self._root_resource.host_id).state != "unconfigured"
        )

        for expected_item in ["interfaces", "lnet"]:
            if expected_item not in devices:
                raise RuntimeError("LinuxNetwork expected but didn't find %s" % expected_item)

        inet4_address_to_interface = {}

        # Get the existing interfaces, get the reported and then delete those that no longer exist.
        current_interface_names = set(interface_name for interface_name in devices["interfaces"])
        existing_interface_names = set(
            interface.name for interface in self.find_by_attr(HostNetworkInterface, host_id=host_id)
        )

        for name in existing_interface_names - current_interface_names:
            self.remove_by_attr(HostNetworkInterface, host_id=host_id, name=name)

        for name, iface in devices["interfaces"].iteritems():
            iface_resource, created = self.update_or_create(
                HostNetworkInterface,
                name=name,
                inet4_address=iface["inet4_address"],
                inet4_prefix=iface["inet4_prefix"],
                host_id=host_id,
                type=iface["type"],
                up=iface["up"],
            )

            iface_resource.rx_bytes = iface["rx_bytes"]
            iface_resource.tx_bytes = iface["tx_bytes"]

            inet4_address_to_interface[iface_resource.name] = iface_resource

        # Get the existing nids, get the reported and then delete those that no longer exist.
        current_nid_names = set(nid_name for nid_name in devices["lnet"]["nids"])
        existing_nid_names = set(nid.name for nid in self.find_by_attr(Nid, host_id=host_id))

        for name in existing_nid_names - current_nid_names:
            self.remove_by_attr(Nid, host_id=host_id, name=name)

        for name, nid in devices["lnet"]["nids"].iteritems():
            parent_interface = inet4_address_to_interface[name]

            assert name == parent_interface.name

            db_nid, created = self.update_or_create(
                Nid,
                parents=[parent_interface],
                name=name,
                host_id=host_id,
                lnd_network=nid["lnd_network"],
                lnd_type=nid["lnd_type"],
            )

            if created:
                self.log.debug(
                    "Learned new nid %s:%s@%s%s"
                    % (parent_interface.host_id, parent_interface.inet4_address, nid["lnd_type"], nid["lnd_network"])
                )

        lnet_state, created = self.update_or_create(LNetState, host_id=host_id, state=devices["lnet"]["state"])
        if created:
            self.log.debug("Learned new lnet modules on %s" % host_id)
