# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader('chroma_agent', 'templates'))

from chroma_common.lib.util import platform_info
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
            if cee.result.rc not in [127, 2, 8]:            # network manager may be uninstalled (127) stopped (8)
                raise
