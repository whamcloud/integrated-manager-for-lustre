import json
import os

from django.db.models import Q


from tests.unit.chroma_core.helper import MockAgentRpc
from tests.unit.chroma_core.helper import MockAgentSsh
from chroma_core.models import Nid
from chroma_core.lib.cache import ObjectCache
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from chroma_core.models import ManagedHost
from chroma_core.services.http_agent import ValidatedClientView

AgentRpc = MockAgentRpc
AgentSsh = MockAgentSsh
MockAgentRpc.mock_servers = {
    'kp-ss-storage-appliance-1': {
        'fqdn': 'kp-ss-storage-appliance-1',
        'nodename': 'kp-ss-storage-appliance-1',
        'nids': [Nid.Nid('192.168.1.22', 'tcp', 0)]
    },
    'kp-ss-storage-appliance-2': {
        'fqdn': 'kp-ss-storage-appliance-2',
        'nodename': 'kp-ss-storage-appliance-2',
        'nids': [Nid.Nid('192.168.1.17', 'tcp', 0)]
    },
}

PRODUCTION_LOCATION = '/usr/share/chroma-manager/tests/framework/gui/mock_agent/'
DEV_LOCATION = "tests/framework/gui/mock_agent/"
LOCATION = DEV_LOCATION if os.path.exists(DEV_LOCATION) else PRODUCTION_LOCATION
MockAgentRpc.mock_servers['kp-ss-storage-appliance-1']['device-plugin'] = json.load(open(os.path.join(LOCATION, 'kp-ss-storage-appliance-1.json')))['result']
MockAgentRpc.mock_servers['kp-ss-storage-appliance-2']['device-plugin'] = json.load(open(os.path.join(LOCATION, 'kp-ss-storage-appliance-2.json')))['result']

# In the absence of monitoring input, ManagedHosts will usually always say 'lnet down' in
# the UI because they're considered offline from a corosync POV: override this for MockAgent
[f for f in ManagedHost._meta.fields if f.name == 'corosync_reported_up'][0].default = True


def _fixup_host_settings(host_id):
    # Give the thing some properties.
    host = ObjectCache.get_by_id(ManagedHost, host_id)
    host.properties = json.dumps({'zfs_installed': False})
    host.save()
    ObjectCache.update(host)

    added_host = ManagedHost.objects.get(id=host_id)
    for host in ManagedHost.objects.filter(~Q(id=host_id)):
        added_host.ha_cluster_peers.add(host)


old_create_host = JobScheduler.create_host


def create_host(self, *args, **kwargs):
    host_id, command_id = old_create_host(self, *args, **kwargs)

    _fixup_host_settings(host_id)

    return host_id, command_id


JobScheduler.create_host = create_host

old_create_host_ssh = JobScheduler.create_host_ssh


def create_host_ssh(self, address, profile, root_pw=None, pkey=None, pkey_pw=None):
    host_id, command_id = old_create_host_ssh(self, address, profile, root_pw, pkey, pkey_pw)

    _fixup_host_settings(host_id)

    return host_id, command_id

JobScheduler.create_host_ssh = create_host_ssh


def test_host_contact(self, address, root_pw=None, pkey=None, pkey_pw=None):
    from chroma_core.models import StepResult, TestHostConnectionJob, Command, TestHostConnectionStep

    ok = address in MockAgentRpc.mock_servers

    result = {
        'address': address,
        'resolve': ok,
        'ping': ok,
        'auth': ok,
        'hostname_valid': ok,
        'fqdn_resolves': ok,
        'fqdn_matches': ok,
        'reverse_resolve': ok,
        'reverse_ping': ok,
        'yum_valid_repos': ok,
        'yum_can_update': ok,
        'openssl': ok,
    }

    command = Command.objects.create(message="Mock Test Host Contact", complete=True)
    job = TestHostConnectionJob.objects.create(state='complete', address=address, root_pw=None, pkey=None, pkey_pw=None)

    command.jobs.add(job)
    StepResult.objects.create(job = job,
                              backtrace = "an error",
                              step_klass = TestHostConnectionStep,
                              args = {'address': address, 'credentials_key': 1},
                              step_index = 0,
                              step_count = 1,
                              state = 'complete',
                              result = json.dumps(result))

    return command.id

JobScheduler.test_host_contact = test_host_contact

ValidatedClientView.valid_certs = {}  # normally set by http_agent service
