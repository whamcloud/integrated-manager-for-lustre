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


"""
Corosync verification
"""

from os import remove
import errno

from chroma_agent.lib.shell import AgentShell
from chroma_agent.lib.corosync import CorosyncRingInterface
from chroma_agent.action_plugins.manage_corosync_common import InterfaceInfo

from chroma_agent.chroma_common.lib.service_control import ServiceControl
from chroma_agent.chroma_common.lib.firewall_control import FirewallControl
from chroma_agent.chroma_common.lib.agent_rpc import agent_error, agent_ok_or_error


PCS_TCP_PORT = 2224

corosync_service = ServiceControl.create('corosync')
pscd_service = ServiceControl.create('pcsd')
firewall_control = FirewallControl.create()


PCS_USER = 'hacluster'
PCS_CLUSTER_NAME = 'lustre-ha-cluster'


def start_corosync2():
    return agent_ok_or_error(corosync_service.enable() or corosync_service.start())


def stop_corosync2():
    return agent_ok_or_error(corosync_service.stop())


def configure_corosync2_stage_1(mcast_port, pcs_password):
    # need to use user "hacluster" which is created on install of "pcs" package,
    # WARNING: clear text password
    set_password_command = ['bash', '-c', 'echo %s | passwd --stdin %s' %
                                          (pcs_password,
                                           PCS_USER)]

    return agent_ok_or_error(AgentShell.run_canned_error_message(set_password_command) or
                             firewall_control.add_rule(mcast_port, "udp", "corosync", persist=True) or
                             firewall_control.add_rule(PCS_TCP_PORT, "tcp", "pcs", persist=True) or
                             pscd_service.start() or
                             corosync_service.enable() or
                             pscd_service.enable())


def configure_corosync2_stage_2(ring0_name, ring1_name, new_node_fqdn, mcast_port, pcs_password, create_cluster):
    """Process configuration including peers and negotiated multicast port, no IP address
    information required

    Note: "The pcs cluster setup command will automatically configure two_node: 1 in
    corosync.conf, so a two-node cluster will "just work". If you are using a different cluster
    shell, you will have to configure corosync.conf appropriately yourself." Therefore
    no-quorum-policy does not have to be set when setting up cluster with pcs.

    :param ring0_name:
    :param ring1_name:
    :param peer_fqdns:
    :param mcast_port:
    :return:
    """

    interfaces = [InterfaceInfo(CorosyncRingInterface(name=ring0_name, ringnumber=0,
                                                      mcastport=mcast_port), None, None),
                  InterfaceInfo(CorosyncRingInterface(name=ring1_name, ringnumber=1,
                                                      mcastport=mcast_port), None, None)]

    config_params = {
        'token': '5000',
        'fail_recv_const': '10',
        'name': 'imltest',
        'transport': 'udp',
        'rrpmode': 'passive',
        'addr0': interfaces[0].corosync_iface.bindnetaddr,
        'addr1': interfaces[1].corosync_iface.bindnetaddr,
        'mcast0': interfaces[0].corosync_iface.mcastaddr,
        'mcast1': interfaces[1].corosync_iface.mcastaddr,
        'mcastport0': interfaces[0].corosync_iface.mcastport,
        'mcastport1': interfaces[1].corosync_iface.mcastport
    }

    # authenticate nodes in cluster
    authenticate_nodes_in_cluster_command = ['pcs', 'cluster', 'auth', new_node_fqdn,
                                             '-u', PCS_USER, '-p', pcs_password]

    # build command string for setup of cluster which will result in corosync.conf rather than
    # writing from template, note we don't start the cluster here as services are managed
    # independently
    if create_cluster:
        cluster_setup_command = ['pcs', 'cluster', 'setup', '--name', PCS_CLUSTER_NAME, '--force'] + [new_node_fqdn]
        for param in ['transport', 'rrpmode', 'addr0', 'mcast0', 'mcastport0', 'addr1', 'mcast1',
                      'mcastport1', 'token', 'fail_recv_const']:
            # pull this value from the dictionary using parameter keyword
            cluster_setup_command.extend(["--" + param, str(config_params[param])])
    else:
        cluster_setup_command = ['pcs', 'cluster', 'node', 'add', new_node_fqdn]

    return agent_ok_or_error(AgentShell.run_canned_error_message(authenticate_nodes_in_cluster_command) or \
                             AgentShell.run_canned_error_message(cluster_setup_command))


def unconfigure_corosync2(host_fqdn, mcast_port):
    """Unconfigure the corosync application.
    For corosync2 don't disable pcsd, just remove host node from cluster and disable corosync from
    auto starting (service should already be stopped by state machine)

    Return: Value using simple return protocol
    """
    error = corosync_service.disable()
    if error:
        return agent_error(error)

    # will fail with "Error: pcsd is not running on <node fqdn>" if not a valid member of cluster
    error = AgentShell.run_canned_error_message(["pcs", "cluster", "node", "remove", host_fqdn])
    if error:
        return agent_error(error)

    # FIXME: do we need to remove the conf file even though pcs removes the reference to 'this' node and syncs?
    try:
        remove("/etc/corosync/corosync.conf")
    except Exception as e:
        if (type(e) is not OSError) or (e.errno != errno.ENOENT):
            return agent_error("Failed to remove corosync.conf")

    return agent_ok_or_error(firewall_control.remove_rule(PCS_TCP_PORT, "tcp", "pcs", persist=True) or
                             firewall_control.remove_rule(mcast_port, "udp", "corosync", persist=True))


ACTIONS = [start_corosync2, stop_corosync2,
           configure_corosync2_stage_1, configure_corosync2_stage_2,
           unconfigure_corosync2]
