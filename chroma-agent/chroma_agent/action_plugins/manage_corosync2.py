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

from chroma_agent.chroma_common.lib import shell
from chroma_agent.lib.system import add_firewall_rule, del_firewall_rule
from chroma_agent.lib.corosync import CorosyncRingInterface, render_config, write_config_to_file

from chroma_agent.chroma_common.lib.agent_rpc import agent_error, agent_result_ok, agent_ok_or_error


def start_corosync2():
    error = shell.run_canned_error_message(['/sbin/service', 'corosync', 'start'])

    if error:
        return agent_error(error)
    else:
        return agent_result_ok


def stop_corosync2():
    return agent_ok_or_error(shell.run_canned_error_message(['/sbin/service', 'corosync', 'stop']))

InterfaceInfo = namedtuple("InterfaceInfo", ['corosync_iface', 'ipaddr', 'prefix'])


def configure_corosync2(peer_fqdns,
                        ring0_name,
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

    error = shell.run_canned_error_message(['/sbin/chkconfig', 'corosync', 'on'])
    if error:
        return agent_error(error)

    return agent_result_ok


def unconfigure_corosync2():
    '''
    Unconfigure the corosync application.

    Return: Value using simple return protocol
    '''

    shell.try_run(['service', 'corosync', 'stop'])
    shell.try_run(['/sbin/chkconfig', 'corosync', 'off'])
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


ACTIONS = [start_corosync2, stop_corosync2,
           configure_corosync2, unconfigure_corosync2]
