#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent.plugins import DevicePlugin
from chroma_agent import shell

import re

EXCLUDE_INTERFACES = ['lo']


class LinuxNetworkDevicePlugin(DevicePlugin):
    def _ifconfig(self):
        result = []
        text = shell.try_run('ifconfig')
        matches = re.finditer("^([\\w]+) .*?RX bytes:(\\d+) .*?TX bytes:(\\d+) .*?^$", text, flags=(re.MULTILINE | re.DOTALL))
        for match in matches:
            name, rx_bytes, tx_bytes = match.groups()
            if name not in EXCLUDE_INTERFACES:
                result.append({
                    'name': name,
                    'rx_bytes': rx_bytes,
                    'tx_bytes': tx_bytes
                    })
        return result

    def start_session(self):
        return self._ifconfig()

    def update_session(self):
        return self._ifconfig()
