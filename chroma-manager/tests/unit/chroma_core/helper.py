
import datetime
import subprocess
import tempfile
import uuid
import re
from dateutil import tz
from collections import defaultdict
from tastypie.serializers import Serializer
import mock

from chroma_core.models import Volume, VolumeNode, ManagedHost, LogMessage, StorageResourceRecord, LNetConfiguration, Nid, ManagedTarget
from chroma_api.authentication import CsrfAuthentication
from chroma_core.lib.cache import ObjectCache
from chroma_core.lib.util import normalize_nid
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from chroma_core.services.log import log_register
from tests.unit.chroma_api.tastypie_test import TestApiClient


log = log_register('test_helper')


def synchronous_run_job(job):
    for step_klass, args in job.get_steps():
        step_klass(job, args, lambda x: None, lambda x: None, mock.Mock()).run(args)


def synthetic_volume(serial = None):
    """
    Create a Volume and an underlying StorageResourceRecord
    """
    volume = Volume.objects.create()

    if serial is None:
        serial = "foobar%d" % volume.id

    attrs = {'serial_80': None,
             'serial_83': serial,
             'size': 1024000}

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


def synthetic_host(address, nids = list([]), storage_resource = False):
    """
    Create a ManagedHost + paraphernalia, with states set as if configuration happened successfully

    :param storage_resource: If true, create a PluginAgentResources (additional overhead, only sometimes required)
    """
    host = ManagedHost.objects.create(
        address = address,
        fqdn = address,
        nodename = address,
        state = 'lnet_up' if nids else 'configured'
    )
    if nids:
        lnet_configuration = LNetConfiguration.objects.create(host = host, state = 'nids_known')
        normalized_nids = [normalize_nid(n) for n in nids]
        for nid in normalized_nids:
            Nid.objects.create(lnet_configuration = lnet_configuration, nid_string = normalize_nid(nid))
    else:
        normalized_nids = []
        LNetConfiguration.objects.create(host = host, state = 'nids_unknown')

    log.debug("synthetic_host: %s %s" % (address, normalized_nids))

    if storage_resource:
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class('linux', 'PluginAgentResources')
        StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {'plugin_name': 'linux', 'host_id': host.id})

    return host


def _passthrough_create_target(target_data):
    ObjectCache.clear()
    return JobScheduler().create_target(target_data)
create_target_patch = mock.patch("chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerRpc.create_target",
                                 new = mock.Mock(side_effect = _passthrough_create_target), create = True)


def _passthrough_create_filesystem(target_data):
    ObjectCache.clear()
    return JobScheduler().create_filesystem(target_data)
create_filesystem_patch = mock.patch("chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerRpc.create_filesystem",
                                     new = mock.Mock(side_effect = _passthrough_create_filesystem), create = True)


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
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        cls.calls.append((cmd, args))
        cls.host_calls[host].append((cmd, args))

        if not cls.succeed:
            cls._fail(host.fqdn)

        if (cmd, args) in cls.fail_commands:
            cls._fail(host.fqdn)

        log.info("invoke_agent %s %s %s" % (host, cmd, args))
        if cmd == "lnet_scan":
            return cls.mock_servers[host.address]['nids']
        elif cmd == 'host_properties':
            return {
                'time': datetime.datetime.utcnow().isoformat() + "Z",
                'fqdn': cls.mock_servers[host.address]['fqdn'],
                'nodename': cls.mock_servers[host.address]['nodename'],
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

            return {'uuid': uuid.uuid1().__str__(), 'inode_count': 666, 'inode_size': inode_size}
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
            return cls.mock_servers[host.address]['detect-scan']
        elif cmd == 'device_plugin' and args['plugin'] == 'lustre':
            return {'lustre': {
                'lnet_up': True,
                'lnet_loaded': True
            }}
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
        elif cmd == 'device_plugin':
            try:
                data = cls.mock_servers[host.address]['device-plugin']
            except KeyError:
                data = {}
            if args['plugin'] in data:
                return {args['plugin']: data[args['plugin']]}
            else:
                raise AgentException(host.fqdn, cmd, args, "")
        elif cmd == 'reboot_server':
            from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
            now = datetime.datetime.utcnow()
            log.info("rebooting %s; updating boot_time to %s" % (host, now))
            JobSchedulerClient.notify(host, now, {'boot_time': now})


class MockAgentSsh(object):
    def __init__(self, address, log = None, console_callback = None, timeout = None):
        self.address = address

    def invoke(self, cmd, args = {}):
        return MockAgentRpc._call(self.address, cmd, args)

    def ssh_params(self):
        return 'root', self.address, 22
