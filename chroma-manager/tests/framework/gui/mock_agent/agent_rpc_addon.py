import json
import os

from django.db.models import Q


from tests.unit.chroma_core.helper import MockAgentRpc
from tests.unit.chroma_core.helper import MockAgentSsh
from chroma_core.models import Nid
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from chroma_core.models import ManagedHost
from chroma_core.services.http_agent import ValidatedClientView
from chroma_core.chroma_common.lib.name_value_list import NameValueList

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


from django.db.models.signals import pre_save
from django.dispatch import receiver


# Whenever the host is saved set the properties and make sure the clusters are in place.
# This isn't efficient because it does it every save, but I don't think that matters for
# the mock
@receiver(pre_save, sender=ManagedHost)
def fixup_host_settings_during_create(**kwargs):
    host = kwargs['instance']

    # Give the thing some properties.
    host.properties = json.dumps({'zfs_installed': False,
                                  'distro': 'CentOS',
                                  'distro_version': 6.6,
                                  'python_version_major_minor': 2.6,
                                  'python_patchlevel': 6,
                                  'kernel_version': '2.6.32-504.8.1.el6_lustre.x86_64'})

    if host.id:
        for clustered_host in ManagedHost.objects.filter(~Q(id=host.id)):
            host.ha_cluster_peers.add(clustered_host)


def test_host_contact(self, address, root_pw=None, pkey=None, pkey_pw=None):
    from chroma_core.models import StepResult, TestHostConnectionJob, Command, TestHostConnectionStep

    ok = address in MockAgentRpc.mock_servers

    status = NameValueList([{'resolve': ok},
                            {'ping': ok},
                            {'auth': ok},
                            {'hostname_valid': ok},
                            {'fqdn_resolves': ok},
                            {'fqdn_matches': ok},
                            {'reverse_resolve': ok},
                            {'reverse_ping': ok},
                            {'yum_valid_repos': ok},
                            {'yum_can_update': ok},
                            {'openssl': ok}])

    result = {
        'address': address,
        'status': status.collection(),
        'valid': ok
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
