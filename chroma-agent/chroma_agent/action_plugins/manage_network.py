# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from iml_common.lib.firewall_control import FirewallControl
from iml_common.lib.agent_rpc import agent_ok_or_error


def open_firewall(port, address, proto, description, persist):
    firewall_control = FirewallControl.create()

    return agent_ok_or_error(firewall_control.add_rule(port, proto, description, persist, address))


def close_firewall(port, address, proto, description, persist):
    firewall_control = FirewallControl.create()

    return agent_ok_or_error(firewall_control.remove_rule(port, proto, description, persist, address))


ACTIONS = [open_firewall, close_firewall]
CAPABILITIES = ['manage_networks']
