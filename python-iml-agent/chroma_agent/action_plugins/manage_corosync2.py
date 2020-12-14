# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
Corosync verification
"""

from chroma_agent.log import console_log
from chroma_agent.lib.shell import AgentShell
from chroma_agent.lib.corosync import CorosyncRingInterface
from chroma_agent.action_plugins.manage_corosync_common import InterfaceInfo

from iml_common.lib.service_control import ServiceControl
from iml_common.lib.firewall_control import FirewallControl
from iml_common.lib.agent_rpc import agent_error
from iml_common.lib.agent_rpc import agent_ok_or_error

PCS_TCP_PORT = 2224

corosync_service = ServiceControl.create("corosync")
pcsd_service = ServiceControl.create("pcsd")
firewall_control = FirewallControl.create()

PCS_USER = "hacluster"
PCS_CLUSTER_NAME = "lustre-ha-cluster"
COROSYNC_CONF_PATH = "/etc/corosync/corosync.conf"


def start_corosync2():
    return agent_ok_or_error(corosync_service.enable() or corosync_service.start())


def stop_corosync2():
    return agent_ok_or_error(corosync_service.stop())


def configure_corosync2_stage_1(mcast_port, pcs_password, fqdn=None):
    # need to use user "hacluster" which is created on install of "pcs" package,
    # WARNING: clear text password
    set_password_command = [
        "bash",
        "-c",
        "echo %s | passwd --stdin %s" % (pcs_password, PCS_USER),
    ]
    if fqdn is not None:
        error = AgentShell.run_canned_error_message(["hostnamectl", "set-hostname", fqdn])
        if error:
            return agent_error(error)

    return agent_ok_or_error(
        AgentShell.run_canned_error_message(set_password_command)
        or firewall_control.add_rule(mcast_port, "udp", "corosync", persist=True)
        or firewall_control.add_rule(PCS_TCP_PORT, "tcp", "pcs", persist=True)
        or pcsd_service.start()
        or corosync_service.enable()
        or pcsd_service.enable()
    )


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

    interfaces = [
        InterfaceInfo(
            CorosyncRingInterface(name=ring0_name, ringnumber=0, mcastport=mcast_port),
            None,
            None,
        ),
        InterfaceInfo(
            CorosyncRingInterface(name=ring1_name, ringnumber=1, mcastport=mcast_port),
            None,
            None,
        ),
    ]

    config_params = {
        "token": "17000",
        "fail_recv_const": "10",
        "transport": "udp",
        "rrpmode": "passive",
        "addr0": interfaces[0].corosync_iface.bindnetaddr,
        "addr1": interfaces[1].corosync_iface.bindnetaddr,
        "mcast0": interfaces[0].corosync_iface.mcastaddr,
        "mcast1": interfaces[1].corosync_iface.mcastaddr,
        "mcastport0": interfaces[0].corosync_iface.mcastport,
        "mcastport1": interfaces[1].corosync_iface.mcastport,
    }

    # authenticate nodes in cluster
    authenticate_nodes_in_cluster_command = [
        "pcs",
        "cluster",
        "auth",
        new_node_fqdn,
        "-u",
        PCS_USER,
        "-p",
        pcs_password,
    ]

    # build command string for setup of cluster which will result in corosync.conf rather than
    # writing from template, note we don't start the cluster here as services are managed
    # independently
    if create_cluster:
        cluster_setup_command = [
            "pcs",
            "cluster",
            "setup",
            "--name",
            PCS_CLUSTER_NAME,
            "--force",
        ] + [new_node_fqdn]
        for param in [
            "transport",
            "rrpmode",
            "addr0",
            "mcast0",
            "mcastport0",
            "addr1",
            "mcast1",
            "mcastport1",
            "token",
            "fail_recv_const",
        ]:
            # pull this value from the dictionary using parameter keyword
            cluster_setup_command.extend(["--" + param, str(config_params[param])])
    else:
        cluster_setup_command = ["pcs", "cluster", "node", "add", new_node_fqdn]

    return agent_ok_or_error(
        AgentShell.run_canned_error_message(authenticate_nodes_in_cluster_command)
        or AgentShell.run_canned_error_message(cluster_setup_command)
    )


def _nodes_in_cluster():
    """
    Returns the nodes in the corosync cluster

    example output from command 'pcs status corosync':
    > Corosync Nodes:
    >  Online:
    >  Offline: bill.bailey.com bob.marley.com

    :return: a list of all nodes in cluster
    """
    nodes = []
    result = AgentShell.run(["pcs", "status", "nodes", "corosync"])

    if result.rc != 0:
        # log all command errors but always continue to remove node from cluster
        console_log.warning(result.stderr)
    else:
        # nodes are on the right side of lines separated with ':'
        for line in result.stdout.split("\n"):
            if line.find(":") > 0:
                nodes.extend(line.split(":")[1].strip().split())

    return nodes


def unconfigure_corosync2(host_fqdn, mcast_port):
    """
    Unconfigure the corosync application.

    For corosync2 don't disable pcsd, just remove host node from cluster and disable corosync from
    auto starting (service should already be stopped in state transition)

    Note that pcs cluster commands handle editing and removal of the corosync.conf file

    Return: Value using simple return protocol
    """
    error = corosync_service.disable()
    if error:
        return agent_error(error)

    # Detect if we are the only node in the cluster, we want to do this before next command removes conf file
    cluster_nodes = _nodes_in_cluster()

    result = AgentShell.run(["pcs", "--force", "cluster", "node", "remove", host_fqdn])

    if result.rc != 0:
        if "No such file or directory" in result.stderr:
            # we want to return successful if the configuration file does not exist
            console_log.warning(result.stderr)
        elif "Error: Unable to update any nodes" in result.stderr:
            # this error is expected when this is the last node in the cluster
            if len(cluster_nodes) != 1:
                return agent_error(result.stderr)
        else:
            return agent_error(result.stderr)

    return agent_ok_or_error(
        firewall_control.remove_rule(PCS_TCP_PORT, "tcp", "pcs", persist=True)
        or firewall_control.remove_rule(mcast_port, "udp", "corosync", persist=True)
    )


ACTIONS = [
    start_corosync2,
    stop_corosync2,
    configure_corosync2_stage_1,
    configure_corosync2_stage_2,
    unconfigure_corosync2,
]
