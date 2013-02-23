#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader('chroma_agent', 'templates'))


def write_ifcfg(device, mac_address, ipv4_address, ipv4_netmask):
    ifcfg_tmpl = env.get_template('ifcfg-nic')
    ifcfg_path = "/etc/sysconfig/network-scripts/ifcfg-%s" % device
    with open(ifcfg_path, "w") as f:
        f.write(ifcfg_tmpl.render(device = device, mac_address = mac_address,
                                  ipv4_address = ipv4_address,
                                  ipv4_netmask = ipv4_netmask))
