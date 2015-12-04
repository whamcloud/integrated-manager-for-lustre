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

from os import remove
from collections import namedtuple
import errno
import re

from chroma_agent.lib.shell import AgentShell
from chroma_agent.lib.system import add_firewall_rule, del_firewall_rule
from chroma_agent.lib.corosync import CorosyncRingInterface, render_config, write_config_to_file
from chroma_agent.lib.corosync import get_ring0, generate_ring1_network, detect_ring1
from chroma_agent.lib.service_control import ServiceControl
from chroma_agent.chroma_common.lib.agent_rpc import agent_error, agent_result_ok, agent_result, agent_ok_or_error


# The window of time in which we count resource monitor failures
RSRC_FAIL_WINDOW = "20m"
# The number of times in the above window a resource monitor can fail
# before we migrate it
RSRC_FAIL_MIGRATION_COUNT = "3"


corosync_service = ServiceControl.create('corosync')


def start_corosync():
    return agent_ok_or_error(corosync_service.start())


def stop_corosync():

    return agent_ok_or_error(corosync_service.stop())


def restart_corosync():
    return agent_ok_or_error(corosync_service.restart())


def check_corosync_enabled():
    return corosync_service.enabled


def enable_corosync():
    return agent_ok_or_error(corosync_service.enable())

InterfaceInfo = namedtuple("InterfaceInfo", ['corosync_iface', 'ipaddr', 'prefix'])


def configure_corosync(ring0_name,
                       mcast_port,
                       ring1_name=None,
                       ring0_ipaddr=None, ring0_prefix=None,
                       ring1_ipaddr=None, ring1_prefix=None):

    interfaces = [InterfaceInfo(CorosyncRingInterface(name=ring0_name,
                                                      ringnumber=0,
                                                      mcastport=mcast_port),
                                ring0_ipaddr,
                                ring0_prefix)]

    if ring1_name:
        interfaces.append(InterfaceInfo(CorosyncRingInterface(ring1_name,
                                                              ringnumber=1,
                                                              mcastport=mcast_port),
                                        ring1_ipaddr,
                                        ring1_prefix))

    for interface in interfaces:
        if interface.ipaddr:
            interface.corosync_iface.set_address(interface.ipaddr, interface.prefix)

    config = render_config([interface.corosync_iface for interface in interfaces])

    write_config_to_file("/etc/corosync/corosync.conf", config)

    add_firewall_rule(mcast_port, "udp", "corosync")

    error = corosync_service.enable()

    if error:
        return agent_error(error)

    return agent_result_ok


def get_cluster_size():
    # you'd think there'd be a way to query the value of a property
    # such as "expected-quorum-votes" but there does not seem to be, so
    # just count nodes instead
    rc, stdout, stderr = AgentShell.run(["crm_node", "-l"])

    if not stdout:
        return 0

    n = 0
    for line in stdout.rstrip().split('\n'):
        node_id, name, status = line.split(" ")
        if status == "member" or status == "lost":
            n += 1

    return n


def unconfigure_corosync():
    """
      Unconfigure the corosync application.

      Return: Value using simple return protocol
    """
    corosync_service.stop()
    corosync_service.disable()
    mcastport = None

    with open("/etc/corosync/corosync.conf") as f:
        for line in f.readlines():
            match = re.match("\s*mcastport:\s*(\d+)", line)
            if match:
                mcastport = match.group(1)
                break
    if mcastport is None:
        return agent_error("Failed to find mcastport in corosync.conf")

    try:
        remove("/etc/corosync/corosync.conf")
    except OSError, e:
        if e.errno != errno.ENOENT:
            return agent_error("Failed to remove corosync.conf")
    except:
        return agent_error("Failed to remove corosync.conf")

    del_firewall_rule(mcastport, "udp", "corosync")

    return agent_result_ok


def get_corosync_autoconfig():
    """
      Automatically detect the configuration for corosync.
      :return: dictionary containing 'result' or 'error'.
    """
    ring0 = get_ring0()

    if not ring0:
        return {'error': 'Failed to detect ring0 interface'}

    ring1_ipaddr, ring1_prefix = generate_ring1_network(ring0)

    ring1 = detect_ring1(ring0, ring1_ipaddr, ring1_prefix)

    if not ring1:
        return agent_error('Failed to detect ring1 interface')

    return agent_result({'interfaces': {ring0.name: {'dedicated': False,
                                                     'ipaddr': ring0.ipv4_address,
                                                     'prefix': ring0.ipv4_prefixlen},
                                        ring1.name: {'dedicated': True,
                                                     'ipaddr': ring1.ipv4_address,
                                                     'prefix': ring1.ipv4_prefixlen}},
                         'mcast_port': ring1.mcastport})


ACTIONS = [start_corosync, stop_corosync,
           configure_corosync, unconfigure_corosync,
           get_corosync_autoconfig]
