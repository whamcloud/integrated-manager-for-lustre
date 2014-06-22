
import datetime
import subprocess
import tempfile
import uuid
import re
from dateutil import tz
from collections import defaultdict
from tastypie.serializers import Serializer
import mock

from chroma_core.models import Volume, VolumeNode, ManagedHost, LogMessage, LNetConfiguration
from chroma_core.models import NetworkInterface, Nid, ManagedTarget, Bundle, Command, ServerProfile
from chroma_api.authentication import CsrfAuthentication
from chroma_core.lib.cache import ObjectCache
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from chroma_core.models import StorageResourceRecord
from chroma_core.services.log import log_register
from tests.unit.chroma_api.tastypie_test import TestApiClient


log = log_register('test_helper')


def synchronous_run_job(job):
    for step_klass, args in job.get_steps():
        step_klass(job, args, lambda x: None, lambda x: None, mock.Mock()).run(args)


def random_str(length=10, prefix='', postfix=''):

    test_string = (str(uuid.uuid4()).translate(None, '-'))[:length]

    return "%s%s%s" % (prefix, test_string, postfix)


def synthetic_volume(serial=None, with_storage=True):
    """
    Create a Volume and an underlying StorageResourceRecord
    """
    volume = Volume.objects.create()

    if not serial:
        serial = "foobar%d" % volume.id

    attrs = {'serial': serial,
             'size': 8192000}

    if with_storage:
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class('linux', 'ScsiDevice')

        storage_resource, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, attrs)

        volume.storage_resource = storage_resource

    volume.save()

    return volume


def synthetic_volume_full(primary_host, *args):
    """
    Create a Volume and some VolumeNodes
    """
    volume = synthetic_volume()
    path = "/fake/path/%s" % volume.id

    VolumeNode.objects.create(volume = volume, host = primary_host, path = path, primary = True)
    for host in args:
        VolumeNode.objects.create(volume = volume, host = host, path = path, primary = False)

    return volume


def synthetic_host_optional_profile(address=None, nids = list([]), storage_resource = False, fqdn = None, nodename = None, server_profile=None):
    """
    Create a ManagedHost + paraphernalia, with states set as if configuration happened successfully

    :param storage_resource: If true, create a PluginAgentResources (additional overhead, only sometimes required)
    """

    if address is None:
        address = random_str(postfix=".tld")

    if fqdn is None:
        fqdn = address
    if nodename is None:
        nodename = address

    host = ManagedHost.objects.create(
        address=address,
        fqdn=fqdn,
        nodename=nodename,
        state='lnet_up' if nids else 'configured',
        server_profile=server_profile
    )

    lnet_configuration = synthetic_host_create_lnet_configuration(host, nids)

    log.debug("synthetic_host: %s %s" % (address, lnet_configuration.get_nids()))

    if storage_resource:
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class('linux', 'PluginAgentResources')
        StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {'plugin_name': 'linux', 'host_id': host.id})

    return host


def synthetic_host(address=None, nids = list([]), storage_resource = False, fqdn = None, nodename = None):

    server_profile = ServerProfile.objects.get(name='test_profile')
    return synthetic_host_optional_profile(address,
                                           nids,
                                           storage_resource,
                                           fqdn,
                                           nodename,
                                           server_profile)


def synthetic_host_create_lnet_configuration(host, nids):
    lnet_configuration, _ = LNetConfiguration.objects.get_or_create(host = host)

    # Now delete any existing nids as we will recreate them if some have been requested.
    Nid.objects.filter(lnet_configuration = lnet_configuration).delete()

    if nids:
        assert(type(nids[0]) == Nid.Nid)

        lnet_configuration.state = 'lnet_up'

        interface_no = 0
        for nid in nids:
            network_interface, _ = NetworkInterface.objects.get_or_create(host = host,
                                                                          name = "eth%s" % interface_no,
                                                                          type = nid.lnd_type)

            network_interface.inet4_address = nid.nid_address
            network_interface.state_up = True
            network_interface.save()

            nid_record = Nid.objects.create(lnet_configuration = lnet_configuration,
                                            network_interface = network_interface)

            nid_record.lnd_network = nid.lnd_network
            nid_record.save()

            interface_no += 1
    else:
        lnet_configuration.state = "lnet_unloaded"

    lnet_configuration.save()

    return lnet_configuration


def create_synthetic_device_info(host, mock_server, plugin):
    ''' Creates the data returned from plugins for integration test purposes. Only does lnet data because
    at present that is all we need. '''

    # Default is an empty dict.
    result = {}

    # First see if there is any explicit mocked data
    try:
        result = mock_server['device-plugin'][plugin]
    except KeyError:
        pass

    # This should come from the simulator, so I am adding to the state of this code.
    # It is a little inconsistent because network devices come and go as nids come and go.
    # really they should be consistent. But I am down to the wire on this and this preserves
    # the current testing correctly. So it is not a step backwards.
    if (plugin == 'linux_network') and (result == {}):
        interfaces = {}
        nids = {}

        if host.state.startswith('lnet'):
            lnet_state = host.state
        else:
            lnet_state = 'lnet_unloaded'

        mock_nids = mock_server['nids']
        interface_no = 0
        if mock_nids:
            for nid in mock_nids:
                name = 'eth%s' % interface_no
                interfaces[name] = {'mac_address': '12:34:56:78:90:%s' % interface_no,
                                    'inet4_address': nid.nid_address,
                                    'inet6_address': 'Need An inet6 Simulated Address',
                                    'type': nid.lnd_type,
                                    'rx_bytes': '24400222349',
                                    'tx_bytes': '1789870413',
                                    'up': True}

                nids[name] = {'nid_address': nid.nid_address,
                              'lnd_type': nid.lnd_type,
                              'lnd_network': nid.lnd_network,
                              'status': '?',
                              'refs': '?',
                              'peer': '?',
                              'rtr': '?',
                              'max': '?',
                              'tx': '?',
                              'min': '?'}

                interface_no += 1

        result = {'interfaces': {'active': interfaces,
                                 'deleted': []},
                  'lnet': {'state': lnet_state,
                           'nids': {'active': nids,
                                    'deleted': []}}}

    return {plugin: result}


def parse_synthentic_device_info(host_id, data):
    ''' Parses the data returned from plugins for integration test purposes. On does lnet data because
        at present that is all we need. '''

    # This creates nid tuples so it can use synthetic_host_create_lnet_configuration to do the
    # actual writes to the database
    for plugin, device_data in data.items():
        if plugin == 'linux_network':
            if len(device_data['lnet']['nids']['active']) > 0:
                nid_tuples = []

                for name, nid in device_data['lnet']['nids']['active'].items():
                    nid_tuples.append(Nid.Nid(nid['nid_address'], nid['lnd_type'], nid['lnd_network']))
            else:
                nid_tuples = None

            synthetic_host_create_lnet_configuration(ManagedHost.objects.get(id = host_id), nid_tuples)


def _passthrough_create_targets(target_data):
    ObjectCache.clear()
    return JobScheduler().create_targets(target_data)
create_targets_patch = mock.patch("chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerRpc.create_targets",
                                 new = mock.Mock(side_effect = _passthrough_create_targets), create = True)


def _passthrough_create_filesystem(target_data):
    ObjectCache.clear()
    return JobScheduler().create_filesystem(target_data)
create_filesystem_patch = mock.patch("chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerRpc.create_filesystem",
                                     new = mock.Mock(side_effect = _passthrough_create_filesystem), create = True)


def _synthetic_create_host_ssh(address, server_profile, root_pw=None, pkey=None, pkey_pw=None):
    host_info = MockAgentRpc.mock_servers[address]
    host = synthetic_host(
        address,
        fqdn=host_info['fqdn'],
        nids=host_info['nids'],
        nodename=host_info['nodename']
    )
    host.server_profile = ServerProfile.objects.get(name=server_profile)
    host.save()

    command = Command.objects.create(message="No-op", complete=True)
    return host, command


create_host_ssh_patch = mock.patch(
    "chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.create_host_ssh",
    new=mock.Mock(side_effect=_synthetic_create_host_ssh))


def freshen(obj):
    return obj.__class__.objects.get(pk=obj.pk)


def generate_csr(common_name):
    # Generate a disposable CSR
    client_key = tempfile.NamedTemporaryFile(delete = False)
    subprocess.call(['openssl', 'genrsa', '-out', client_key.name, '2048'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    csr = subprocess.Popen(['openssl', "req", "-new", "-subj", "/C=/ST=/L=/O=/CN=%s" % common_name, "-key", client_key.name],
                           stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()[0]
    return csr


def fake_log_message(message):
    t = datetime.datetime.utcnow()
    t = t.replace(tzinfo = tz.tzutc())
    return LogMessage.objects.create(
        datetime = t,
        message = message,
        severity = 0,
        facility = 0,
        tag = "",
        message_class = LogMessage.get_message_class(message)
    )


def load_default_bundles():
    Bundle.objects.create(bundle_name='lustre', location='/tmp/',
                          description='Lustre Bundle')
    Bundle.objects.create(bundle_name='agent', location='/tmp/',
                          description='Agent Bundle')
    Bundle.objects.create(bundle_name='agent_dependencies', location='/tmp/',
                          description='Agent Dependency Bundle')


def load_default_profile():
    load_default_bundles()
    default_sp = ServerProfile(name='test_profile', ui_name='Managed storage server',
                               ui_description='A storage server suitable for creating new HA-enabled filesystem targets',
                               managed=True)
    default_sp.bundles.add('lustre')
    default_sp.bundles.add('agent')
    default_sp.bundles.add('agent_dependencies')
    default_sp.save()


class MockAgentRpc(object):
    mock_servers = {}
    calls = []
    host_calls = defaultdict(list)

    @classmethod
    def start(cls):
        pass

    @classmethod
    def shutdown(cls):
        pass

    @classmethod
    def clear_calls(cls):
        cls.calls = []

    @classmethod
    def last_call(cls):
        return cls.calls[-1]

    succeed = True
    fail_commands = []
    selinux_enabled = False
    version = None
    capabilities = ['manage_targets']

    @classmethod
    def remove(cls, fqdn):
        pass

    @classmethod
    def _fail(cls, fqdn):
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        log.error("Synthetic agent error on host %s" % fqdn)
        raise AgentException(fqdn, "cmd", {'foo': 'bar'}, "Fake backtrace")

    @classmethod
    def call(cls, fqdn, cmd, args, cancel_event):
        from chroma_core.services.job_scheduler import job_scheduler
        import django.db

        # If the DB was disabled for the Step within which we're run, we need to re-enable
        # DB access temporarily to run the mock agent ops
        db_disabled = django.db.connection.connection == job_scheduler.DISABLED_CONNECTION
        try:
            if db_disabled:
                django.db.connection.connection = None

            from chroma_core.services.job_scheduler.agent_rpc import ActionInFlight
            host = ManagedHost.objects.get(fqdn = fqdn)
            result = cls._call(host, cmd, args)
            action_state = ActionInFlight('foo', fqdn, cmd, args)
            action_state.subprocesses = []
            return result, action_state
        finally:
            if db_disabled:
                django.db.connection.connection = job_scheduler.DISABLED_CONNECTION

    @classmethod
    def _call(cls, host, cmd, args):
        cls.calls.append((cmd, args))
        cls.host_calls[host].append((cmd, args))

        if not cls.succeed:
            cls._fail(host.fqdn)

        if (cmd, args) in cls.fail_commands:
            cls._fail(host.fqdn)

        mock_server = cls.mock_servers[host.address]

        log.info("invoke_agent %s %s %s" % (host, cmd, args))

        # This isn't really accurate because lnet is scanned asynchonously, but it is as close as we can get today
        # Fixme: Also I know think this is writing to the wrong thing and should be changing the mock_server entries.
        # to lnet_up, I guess the mock_server needs an lnet state really, rather than relying on nids present.
        if cmd == "load_lnet":
            synthetic_host_create_lnet_configuration(host, mock_server['nids'])
            return
        elif cmd == "device_plugin":
            # Only returns nid info today.
            return create_synthetic_device_info(host, mock_server, args['plugin'])
        elif cmd == 'host_properties':
            return {
                'time': datetime.datetime.utcnow().isoformat() + "Z",
                'fqdn': mock_server['fqdn'],
                'nodename': mock_server['nodename'],
                'capabilities': cls.capabilities,
                'selinux_enabled': cls.selinux_enabled,
                'agent_version': cls.version,
            }
        elif cmd == 'format_target':
            inode_size = None
            if 'mkfsoptions' in args:
                inode_arg = re.search("-I (\d+)", args['mkfsoptions'])
                if inode_arg:
                    inode_size = int(inode_arg.group(1).__str__())

            if inode_size is None:
                # A 'foo' value
                inode_size = 777

            return {'uuid': uuid.uuid1().__str__(),
                    'inode_count': 666,
                    'inode_size': inode_size,
                    'filesystem_type': 'ext4'}
        elif cmd == 'stop_target':
            ha_label = args['ha_label']
            target = ManagedTarget.objects.get(ha_label = ha_label)
            return
        elif cmd == 'start_target':
            ha_label = args['ha_label']
            target = ManagedTarget.objects.get(ha_label = ha_label)
            return {'location': target.primary_server().nodename}
        elif cmd == 'register_target':
            # Assume mount paths are "/mnt/testfs-OST0001" style
            mount_point = args['mount_point']
            label = re.search("/mnt/([^\s]+)", mount_point).group(1)
            return {'label': label}
        elif cmd == 'detect_scan':
            return mock_server['detect-scan']
        elif cmd == 'register_server':
            api_client = TestApiClient()
            old_is_authenticated = CsrfAuthentication.is_authenticated
            try:
                CsrfAuthentication.is_authenticated = mock.Mock(return_value = True)
                api_client.client.login(username = 'debug', password = 'chr0m4_d3bug')
                fqdn = cls.mock_servers[host]['fqdn']

                response = api_client.post(args['url'] + "register/%s/" % args['secret'], data = {
                    'address': host,
                    'fqdn': fqdn,
                    'nodename': cls.mock_servers[host]['nodename'],
                    'capabilities': ['manage_targets'],
                    'version': cls.version,
                    'csr': generate_csr(fqdn)
                })
                assert response.status_code == 201
                registration_data = Serializer().deserialize(response.content, format = response['Content-Type'])
                print "MockAgent.invoke returning %s" % registration_data
                return registration_data
            finally:
                CsrfAuthentication.is_authenticated = old_is_authenticated
        elif cmd == 'kernel_status':
            return {
                'running': 'fake_kernel-0.1',
                'required': 'fake_kernel-0.1',
                'available': ['fake_kernel-0.1']
            }
        elif cmd == 'reboot_server':
            from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
            now = datetime.datetime.utcnow()
            log.info("rebooting %s; updating boot_time to %s" % (host, now))
            JobSchedulerClient.notify(host, now, {'boot_time': now})
        elif 'socket.gethostbyname(socket.gethostname())' in cmd:
            if not mock_server['tests']['hostname_valid']:
                return '127.0.0.1'
            else:
                return mock_server['address']
        elif 'socket.getfqdn()' in cmd:
            return mock_server['self_fqdn']
        elif 'ping' in cmd:
            result = ((0 if mock_server['tests']['reverse_resolve'] else 2) +
                      (0 if mock_server['tests']['reverse_ping'] else 1))
            return result
        elif 'rpm -q epel-release' in cmd:
            return 1 if mock_server['tests']['yum_valid_repos'] else 0
        elif cmd == 'yum info ElectricFence':
            return 0 if mock_server['tests']['yum_can_update'] else 1


class MockAgentSsh(object):
    ssh_should_fail = False

    def __init__(self, address, log = None, console_callback = None, timeout = None):
        self.address = address

    def construct_ssh_auth_args(self, root_pw, pkey, pkey_pw):
        return {}

    def invoke(self, cmd, args = {}, auth_args = None):
        host = ManagedHost(address = self.address)
        return MockAgentRpc._call(host, cmd, args)

    def ssh(self, cmd, auth_args = None):
        if self.ssh_should_fail:
            from paramiko import SSHException
            raise SSHException("synthetic failure")

        result = self.invoke(cmd, auth_args)
        if isinstance(result, int):
            return (result, "", "")
        else:
            return (0, result, "")

    def ssh_params(self):
        return 'root', self.address, 22
