# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.
import errno
from jinja2 import Environment, PackageLoader
from chroma_agent.lib.shell import AgentShell

env = Environment(loader=PackageLoader("chroma_agent", "templates"))

NM_STOPPED_RC = 8  # network manager stopped


def write_ifcfg(device, mac_address, ipv4_address, ipv4_netmask):
    ifcfg_tmpl = env.get_template("ifcfg-nic")
    ifcfg_path = "/etc/sysconfig/network-scripts/ifcfg-%s" % device
    with open(ifcfg_path, "w") as f:
        f.write(
            ifcfg_tmpl.render(
                device=device,
                mac_address=mac_address,
                ipv4_address=ipv4_address,
                ipv4_netmask=ipv4_netmask,
            )
        )

    return ifcfg_path


def unmanage_network(device, mac_address):
    """
    Rewrite the network configuration file to set NM_CONTROLLED="no"

    TODO: This is destructive and overwrites the file clearing
    previously configured settings, needs fixing.
    """
    ifcfg_path = write_ifcfg(device, mac_address, None, None)

    if ifcfg_path:
        try:
            AgentShell.try_run(["nmcli", "con", "load", ifcfg_path])
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise e
        except AgentShell.CommandExecutionError as cee:
            if cee.result.rc != NM_STOPPED_RC:
                raise cee
