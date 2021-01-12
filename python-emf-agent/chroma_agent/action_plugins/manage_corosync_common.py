# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
Corosync verification
"""

from collections import namedtuple

from chroma_agent.lib.corosync import (
    get_shared_ring,
    generate_ring1_network,
    detect_ring1,
    RingDetectionError,
    CorosyncRingInterface,
)
from emf_common.lib.agent_rpc import agent_error, agent_result_ok, agent_result


InterfaceInfo = namedtuple("InterfaceInfo", ["corosync_iface", "ipaddr", "prefix"])


def get_corosync_autoconfig():
    """
    Automatically detect the configuration for corosync.
    :return: dictionary containing 'result' or 'error'.
    """
    ring0 = get_shared_ring()

    if not ring0:
        return agent_error("Failed to detect ring0 interface")

    ring1_ipaddr, ring1_prefix = generate_ring1_network(ring0)

    try:
        ring1 = detect_ring1(ring0, ring1_ipaddr, ring1_prefix)
    except RingDetectionError as e:
        return agent_error(e.message)

    return agent_result(
        {
            "interfaces": {
                ring0.name: {
                    "dedicated": False,
                    "ipaddr": ring0.ipv4_address,
                    "prefix": ring0.ipv4_prefixlen,
                },
                ring1.name: {
                    "dedicated": True,
                    "ipaddr": ring1.ipv4_address,
                    "prefix": ring1.ipv4_prefixlen,
                },
            },
            "mcast_port": ring1.mcastport,
        }
    )


def configure_network(
    ring0_name,
    ring1_name=None,
    ring0_ipaddr=None,
    ring0_prefix=None,
    ring1_ipaddr=None,
    ring1_prefix=None,
):
    """
    Configure rings, bring up interfaces and set addresses. no multicast port or peers specified.
    """
    interfaces = [
        InterfaceInfo(
            CorosyncRingInterface(name=ring0_name, ringnumber=0),
            ring0_ipaddr,
            ring0_prefix,
        )
    ]

    if ring1_name:
        interfaces.append(
            InterfaceInfo(
                CorosyncRingInterface(ring1_name, ringnumber=1),
                ring1_ipaddr,
                ring1_prefix,
            )
        )

    for interface in interfaces:
        interface.corosync_iface.set_address(interface.ipaddr, interface.prefix)

    return agent_result_ok


ACTIONS = [get_corosync_autoconfig, configure_network]
