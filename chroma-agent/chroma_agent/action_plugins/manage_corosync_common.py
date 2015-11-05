#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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


"""
Corosync verification
"""

from collections import namedtuple

from chroma_agent.lib.corosync import get_ring0, generate_ring1_network, detect_ring1, RingDetectionError, CorosyncRingInterface
from chroma_agent.chroma_common.lib.agent_rpc import agent_error, agent_result_ok, agent_result


InterfaceInfo = namedtuple("InterfaceInfo", ['corosync_iface', 'ipaddr', 'prefix'])


def get_corosync_autoconfig():
    """
    Automatically detect the configuration for corosync.
    :return: dictionary containing 'result' or 'error'.
    """
    ring0 = get_ring0()

    if not ring0:
        return agent_error('Failed to detect ring0 interface')

    ring1_ipaddr, ring1_prefix = generate_ring1_network(ring0)

    try:
        ring1 = detect_ring1(ring0, ring1_ipaddr, ring1_prefix)
    except RingDetectionError as e:
        return agent_error(e.message)

    return agent_result({'interfaces': {ring0.name: {'dedicated': False,
                                                     'ipaddr': ring0.ipv4_address,
                                                     'prefix': ring0.ipv4_prefixlen},
                                        ring1.name: {'dedicated': True,
                                                     'ipaddr': ring1.ipv4_address,
                                                     'prefix': ring1.ipv4_prefixlen}},
                         'mcast_port': ring1.mcastport})


def configure_network(ring0_name, ring1_name=None,
                      ring0_ipaddr=None, ring0_prefix=None,
                      ring1_ipaddr=None, ring1_prefix=None):
    """
    Configure rings, bring up interfaces and set addresses. no multicast port or peers specified.
    """
    interfaces = [InterfaceInfo(CorosyncRingInterface(name=ring0_name, ringnumber=0),
                                ring0_ipaddr, ring0_prefix)]

    if ring1_name:
        interfaces.append(InterfaceInfo(CorosyncRingInterface(ring1_name, ringnumber=1),
                                        ring1_ipaddr, ring1_prefix))

    for interface in interfaces:
        if interface.ipaddr and interface.ipaddr == ring1_ipaddr:
            # we only want to set ring1, ring0 already set and should not be modified
            interface.corosync_iface.set_address(interface.ipaddr, interface.prefix)

    return agent_result_ok


ACTIONS = [get_corosync_autoconfig, configure_network]
