# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
Corosync verification
"""

from os import remove
from collections import namedtuple
import errno
import re

from emf_common.lib.service_control import ServiceControl
from emf_common.lib.firewall_control import FirewallControl

from chroma_agent.lib.corosync import (
    CorosyncRingInterface,
    render_config,
    write_config_to_file,
)
from emf_common.lib.agent_rpc import agent_error, agent_result_ok, agent_ok_or_error

corosync_service = ServiceControl.create("corosync")
firewall_control = FirewallControl.create()


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


InterfaceInfo = namedtuple("InterfaceInfo", ["corosync_iface", "ipaddr", "prefix"])


def configure_corosync(ring0_name, ring1_name, old_mcast_port, new_mcast_port):
    """
    Process configuration including negotiated multicast port, no IP address information required

    :param ring0_name:
    :param ring1_name:
    :param old_mcast_port: None if we are configuring corosync for the first-time, present if changing mcast port
    :param new_mcast_port: desired corosync multicast port as configured by user
    :return: Value using simple return protocol
    """

    interfaces = [
        InterfaceInfo(
            CorosyncRingInterface(name=ring0_name, ringnumber=0, mcastport=new_mcast_port),
            None,
            None,
        ),
        InterfaceInfo(
            CorosyncRingInterface(name=ring1_name, ringnumber=1, mcastport=new_mcast_port),
            None,
            None,
        ),
    ]

    config = render_config([interface.corosync_iface for interface in interfaces])

    write_config_to_file("/etc/corosync/corosync.conf", config)

    if old_mcast_port is not None:
        error = firewall_control.remove_rule(old_mcast_port, "udp", "corosync", persist=True)

        if error:
            return agent_error(error)

    return agent_ok_or_error(
        firewall_control.add_rule(new_mcast_port, "udp", "corosync", persist=True) or corosync_service.enable()
    )


def unconfigure_corosync():
    """
    Unconfigure the corosync application.

    :return: Value using simple return protocol
    """
    corosync_service.stop()
    corosync_service.disable()
    mcast_port = None

    with open("/etc/corosync/corosync.conf") as f:
        for line in f.readlines():
            match = re.match("\s*mcastport:\s*(\d+)", line)
            if match:
                mcast_port = match.group(1)
                break
    if mcast_port is None:
        return agent_error("Failed to find mcastport in corosync.conf")

    try:
        remove("/etc/corosync/corosync.conf")
    except OSError as e:
        if e.errno != errno.ENOENT:
            return agent_error("Failed to remove corosync.conf")
    except:
        return agent_error("Failed to remove corosync.conf")

    error = firewall_control.remove_rule(mcast_port, "udp", "corosync", persist=True)

    if error:
        return agent_error(error)

    return agent_result_ok


ACTIONS = [start_corosync, stop_corosync, configure_corosync, unconfigure_corosync]
