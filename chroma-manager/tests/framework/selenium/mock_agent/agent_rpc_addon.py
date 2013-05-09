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
import os
PRODUCTION_LOCATION = '/usr/share/chroma-manager/tests/framework/selenium/mock_agent/'
DEV_LOCATION = "tests/framework/selenium/mock_agent/"
LOCATION = DEV_LOCATION if os.path.exists(DEV_LOCATION) else PRODUCTION_LOCATION
MockAgentRpc.mock_servers['kp-ss-storage-appliance-1']['device-plugin'] = json.load(open(os.path.join(LOCATION, 'kp-ss-storage-appliance-1.json')))['result']
MockAgentRpc.mock_servers['kp-ss-storage-appliance-2']['device-plugin'] = json.load(open(os.path.join(LOCATION, 'kp-ss-storage-appliance-2.json')))['result']

# In the absence of monitoring input, ManagedHosts will usually always say 'lnet down' in
# the UI because they're considered offline from a corosync POV: override this for MockAgent
from chroma_core.models import ManagedHost
[f for f in ManagedHost._meta.fields if f.name == 'corosync_reported_up'][0].default = True

from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
old_create_host = JobScheduler.create_host


def create_host(self, *args, **kwargs):
    from chroma_core.models import ManagedHost
    from django.db.models import Q
    host_id, command_id = old_create_host(self, *args, **kwargs)
    added_host = ManagedHost.objects.get(id=host_id)
    for host in ManagedHost.objects.filter(~Q(id=host_id)):
        added_host.ha_cluster_peers.add(host)

    return host_id, command_id

JobScheduler.create_host = create_host


def test_host_contact(self, address, root_pw=None, pkey=None, pkey_pw=None):
    ok = address in MockAgentRpc.mock_servers
    return {
        'address': ok,
        'resolve': ok,
        'ping': ok,
        'auth': ok,
        'agent': ok,
        'reverse_resolve': ok,
        'reverse_ping': ok
    }

JobScheduler.test_host_contact = test_host_contact

from chroma_core.services.http_agent import MessageView
MessageView.valid_certs = {}  # normally set by http_agent service
