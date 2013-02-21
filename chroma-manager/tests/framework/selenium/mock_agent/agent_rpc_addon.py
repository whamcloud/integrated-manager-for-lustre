
from tests.unit.chroma_core.helper import MockAgentRpc
from tests.unit.chroma_core.helper import MockAgentSsh
AgentRpc = MockAgentRpc
AgentSsh = MockAgentSsh
MockAgentRpc.mock_servers = {
    'kp-ss-storage-appliance-1': {
        'fqdn': 'kp-ss-storage-appliance-1',
        'nodename': 'kp-ss-storage-appliance-1',
        'nids': ['192.168.1.22@tcp']
    },
    'kp-ss-storage-appliance-2': {
        'fqdn': 'kp-ss-storage-appliance-2',
        'nodename': 'kp-ss-storage-appliance-2',
        'nids': ['192.168.1.17@tcp']
    },
}

import json
MockAgentRpc.mock_servers['kp-ss-storage-appliance-1']['device-plugin'] = json.load(open('/usr/share/chroma-manager/kp-ss-storage-appliance-1.json'))['result']
MockAgentRpc.mock_servers['kp-ss-storage-appliance-2']['device-plugin'] = json.load(open('/usr/share/chroma-manager/kp-ss-storage-appliance-2.json'))['result']

# In the absence of monitoring input, ManagedHosts will usually always say 'lnet down' in
# the UI because they're considered offline from a corosync POV: override this for MockAgent
from chroma_core.models import ManagedHost
[f for f in ManagedHost._meta.fields if f.name == 'corosync_reported_up'][0].default = True
