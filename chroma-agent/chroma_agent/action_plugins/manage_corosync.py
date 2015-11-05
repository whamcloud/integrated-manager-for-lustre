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

from chroma_agent.chroma_common.lib.service_control import ServiceControl
from chroma_agent.chroma_common.lib.firewall_control import FirewallControl

from chroma_agent.lib.corosync import CorosyncRingInterface, render_config, write_config_to_file
from chroma_agent.chroma_common.lib.agent_rpc import agent_error, agent_result_ok, agent_ok_or_error


corosync_service = ServiceControl.create('corosync')
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

InterfaceInfo = namedtuple("InterfaceInfo", ['corosync_iface', 'ipaddr', 'prefix'])


def configure_corosync(ring0_name, ring1_name, mcast_port):
    """
    Process configuration including negotiated multicast port, no IP address information required
    :param ring0_name:
    :param ring1_name:
    :param mcast_port:
    :return:
    """

    interfaces = [InterfaceInfo(CorosyncRingInterface(name=ring0_name, ringnumber=0, mcastport=mcast_port), None, None),
                  InterfaceInfo(CorosyncRingInterface(name=ring1_name, ringnumber=1, mcastport=mcast_port), None, None)]

    config = render_config([interface.corosync_iface for interface in interfaces])

    write_config_to_file("/etc/corosync/corosync.conf", config)

    error = firewall_control.add_rule(mcast_port, "udp", "corosync", persist=True)

    if error:
        return agent_error(error)

    return agent_ok_or_error(corosync_service.enable())


def unconfigure_corosync():
    """
      Unconfigure the corosync application.

      Return: Value using simple return protocol
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
    except OSError, e:
        if e.errno != errno.ENOENT:
            return agent_error("Failed to remove corosync.conf")
    except:
        return agent_error("Failed to remove corosync.conf")

    error = firewall_control.remove_rule(mcast_port, "udp", "corosync", persist=True)

    if error:
        return agent_error(error)

    return agent_result_ok


ACTIONS = [start_corosync, stop_corosync,
           configure_corosync, unconfigure_corosync]
