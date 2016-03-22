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


from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader('chroma_agent', 'templates'))

from chroma_agent.chroma_common.lib.util import platform_info
from chroma_agent.lib.shell import AgentShell


def write_ifcfg(device, mac_address, ipv4_address, ipv4_netmask):
    ifcfg_tmpl = env.get_template('ifcfg-nic')
    ifcfg_path = "/etc/sysconfig/network-scripts/ifcfg-%s" % device
    with open(ifcfg_path, "w") as f:
        f.write(ifcfg_tmpl.render(device = device, mac_address = mac_address,
                                  ipv4_address = ipv4_address,
                                  ipv4_netmask = ipv4_netmask))

    return ifcfg_path


def unmanage_network(device, mac_address):
    """Rewrite the network configuration file to set NM_CONTROLLED="no"
    TODO: This is destructive and overwrites the file loosing all settings.
    This needs to be fixed up.
    """
    ifcfg_path = write_ifcfg(device, mac_address, None, None)

    if platform_info.distro_version >= 7.0:
        try:
            AgentShell.try_run(['nmcli', 'con', 'load', ifcfg_path])
        except AgentShell.CommandExecutionError as cee:
            if cee.result.rc != 127:            # The user may have uninstalled network manager.
                raise
