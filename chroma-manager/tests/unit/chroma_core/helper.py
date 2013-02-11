from collections import defaultdict
from contextlib import contextmanager
import datetime
import subprocess
import tempfile
from chroma_api.authentication import CsrfAuthentication
from chroma_core.lib.cache import ObjectCache
from chroma_core.services.log import log_register
from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonRpcInterface
from dateutil import tz
from django.test import TestCase
import mock
from chroma_core.models.jobs import Command
from chroma_core.models import Volume, VolumeNode, ManagedHost, LogMessage, StorageResourceRecord
from chroma_core.services.queue import ServiceQueue
from chroma_core.services.rpc import ServiceRpcInterface
import re
from tastypie.serializers import Serializer
from tests.unit.chroma_api.tastypie_test import TestApiClient


log = log_register('test_helper')


def synthetic_volume(serial = None):
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
        message_class = 0,
        severity = 0,
        facility = 0,
        tag = ""
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
        from chroma_core.services.job_scheduler.agent_rpc import ActionInFlight
        host = ManagedHost.objects.get(fqdn = fqdn)
        result = cls._call(host, cmd, args)
        action_state = ActionInFlight('foo', fqdn, cmd, args)
        action_state.subprocesses = []
        return result, action_state

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
            import uuid
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
            from chroma_core.models import ManagedTarget
            ha_label = args['ha_label']
            target = ManagedTarget.objects.get(ha_label = ha_label)
            return
        elif cmd == 'start_target':
            from chroma_core.models import ManagedTarget
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


class MockAgentSsh(object):
    def __init__(self, address, log = None, console_callback = None, timeout = None):
        self.address = address

    def invoke(self, cmd, args = {}):
        return MockAgentRpc._call(self.address, cmd, args)

    def ssh_params(self):
        return 'root', self.address, 22


class JobTestCase(TestCase):
    mock_servers = None
    hosts = None

    def _create_host(self, address):
        return ManagedHost.create(
            self.mock_servers[address]['fqdn'],
            self.mock_servers[address]['nodename'],
            ['manage_targets'],
            address = address)[0]

    @contextmanager
    def assertInvokes(self, agent_command, agent_args):
        initial_call_count = len(MockAgentRpc.calls)
        yield
        wrapped_calls = MockAgentRpc.calls[initial_call_count:]
        for cmd, args in wrapped_calls:
            if cmd == agent_command and args == agent_args:
                return
        raise self.failureException("Command '%s', %s was not invoked (calls were: %s)" % (agent_command, agent_args, wrapped_calls))

    def _test_lun(self, primary_host, *args):
        volume = synthetic_volume()
        path = "/fake/path/%s" % volume.id

        VolumeNode.objects.create(volume = volume, host = primary_host, path = path, primary = True)
        for host in args:
            VolumeNode.objects.create(volume = volume, host = host, path = path, primary = False)

        return volume

    def set_state(self, obj, state, check = True, run = True):
        command = Command.set_state([(obj, state)], "Unit test transition %s to %s" % (obj, state), run = run)
        if check:
            if command:
                self.assertEqual(Command.objects.get(pk = command.id).complete, True)
            try:
                self.assertState(obj, state)
            except obj.__class__.DoesNotExist:
                pass

    def set_state_delayed(self, obj_state_pairs):
        """Schedule some jobs without executing them"""
        Command.set_state(obj_state_pairs, "Unit test transition", run = False)

    def set_state_complete(self):
        """Run any outstanding jobs"""
        self.job_scheduler._run_next()
        self.assertEqual(Command.objects.filter(complete = False).count(), 0)

    def assertState(self, obj, state):
        self.assertEqual(freshen(obj).state, state)

    def setUp(self):
        from chroma_core.services.http_agent import AgentSessionRpc
        from chroma_core.services.http_agent import Service as HttpAgentService
        # FIXME: have to do self before every test because otherwise
        # one test will get all the setup of StoragePluginClass records,
        # the in-memory instance of storage_plugin_manager will expect
        # them to still be there but they'll have been cleaned
        # out of the database.  Setting up self stuff should be done
        # as part of the initial DB setup before any test is started
        # so that it's part of the baseline that's rolled back to
        # after each test.
        import chroma_core.lib.storage_plugin.manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = chroma_core.lib.storage_plugin.manager.StoragePluginManager()

        # Intercept attempts to call out to lustre servers
        import chroma_core.services.job_scheduler.agent_rpc
        self.old_agent_rpc = chroma_core.services.job_scheduler.agent_rpc.AgentRpc
        self.old_agent_ssh = chroma_core.services.job_scheduler.agent_rpc.AgentSsh
        MockAgentRpc.mock_servers = self.mock_servers

        chroma_core.services.job_scheduler.agent_rpc.AgentRpc = MockAgentRpc
        chroma_core.services.job_scheduler.agent_rpc.AgentSsh = MockAgentSsh

        # Any RPCs that are going to get called need explicitly overriding to
        # turn into local calls -- self is a catch-all to prevent any RPC classes
        # from trying to do network comms during unit tests
        ServiceRpcInterface._call = mock.Mock(side_effect = NotImplementedError)
        ServiceQueue.put = mock.Mock(side_effect = NotImplementedError)

        # Create an instance for the purposes of the test
        from chroma_core.services.plugin_runner.resource_manager import ResourceManager
        resource_manager = ResourceManager()
        from chroma_core.services.plugin_runner import AgentPluginHandlerCollection

        def patch_daemon_rpc(rpc_class, test_daemon):
            # Patch AgentDaemonRpc to call our instance instead of trying to do an RPC
            def rpc_local(fn_name, *args, **kwargs):
                retval = getattr(test_daemon, fn_name)(*args, **kwargs)
                log.info("patch_daemon_rpc: %s(%s %s) -> %s" % (fn_name, args, kwargs, retval))
                return retval

            rpc_class._call = mock.Mock(side_effect = rpc_local)

        patch_daemon_rpc(AgentDaemonRpcInterface, AgentPluginHandlerCollection(resource_manager))

        patch_daemon_rpc(AgentSessionRpc, HttpAgentService())

        from chroma_core.services.job_scheduler.dep_cache import DepCache
        from chroma_core.services.job_scheduler.job_scheduler import JobScheduler, RunJobThread
        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerRpc, NotificationQueue
        self.job_scheduler = JobScheduler()
        patch_daemon_rpc(JobSchedulerRpc, self.job_scheduler)

        from chroma_core.services.job_scheduler import QueueHandler
        job_scheduler_queue_handler = QueueHandler(self.job_scheduler)

        def job_scheduler_queue_immediate(body):
            log.info("job_scheduler_queue_immediate: %s" % body)
            job_scheduler_queue_handler.on_message(body)
        NotificationQueue.put = mock.Mock(side_effect = job_scheduler_queue_immediate)

        def spawn_job(job):
            thread = RunJobThread(self.job_scheduler, job)
            self.job_scheduler._run_threads[job.id] = thread
            thread.run()

        JobScheduler._spawn_job = mock.Mock(side_effect=spawn_job)

        def run_next():
            while True:
                runnable_jobs = self.job_scheduler._job_collection.ready_jobs

                log.info("run_next: %d runnable jobs of (%d pending, %d tasked)" % (
                    len(runnable_jobs),
                    len(self.job_scheduler._job_collection.pending_jobs),
                    len(self.job_scheduler._job_collection.tasked_jobs)))

                if not runnable_jobs:
                    break

                dep_cache = DepCache()
                ok_jobs, cancel_jobs = self.job_scheduler._check_jobs(runnable_jobs, dep_cache)
                self.job_scheduler._job_collection.update_many(ok_jobs, 'tasked')
                for job in cancel_jobs:
                    self.job_scheduler._complete_job(job, False, True)
                for job in ok_jobs:
                    self.job_scheduler._spawn_job(job)

        JobScheduler._run_next = mock.Mock(side_effect=run_next)

        def complete_job(job, errored = False, cancelled = False):
            ObjectCache.clear()
            self.job_scheduler._complete_job(job, errored, cancelled)

        JobScheduler.complete_job = mock.Mock(side_effect=complete_job)

        # Patch host removal because we use a _test_lun function that generates Volumes
        # with no corresponding StorageResourceRecords, so the real implementation wouldn't
        # remove them
        def fake_remove_host_resources(host_id):
            from chroma_core.models.host import Volume, VolumeNode
            for vn in VolumeNode.objects.filter(host__id = host_id):
                vn.mark_deleted()
            for volume in Volume.objects.all():
                if volume.volumenode_set.count() == 0:
                    volume.mark_deleted()

        AgentDaemonRpcInterface.remove_host_resources = mock.Mock(side_effect = fake_remove_host_resources)

    def tearDown(self):
        import chroma_core.services.job_scheduler.agent_rpc
        chroma_core.services.job_scheduler.agent_rpc.AgentRpc = self.old_agent_rpc
        chroma_core.services.job_scheduler.agent_rpc.AgentSsh = self.old_agent_ssh


class JobTestCaseWithHost(JobTestCase):
    mock_servers = {
            'myaddress': {
                'fqdn': 'myaddress.mycompany.com',
                'nodename': 'test01.myaddress.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            }
    }

    def setUp(self):
        super(JobTestCaseWithHost, self).setUp()

        from chroma_core.models import ManagedHost
        self.hosts = [ManagedHost.create(info['fqdn'], info['nodename'], ['manage_targets'], address = address)[0] for address, info in self.mock_servers.items()]

        # Handy if you're only using one
        self.host = self.hosts[0]
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

    def create_simple_filesystem(self, start = True):
        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem
        self.mgt = ManagedMgs.create_for_volume(self._test_lun(self.host).id, name = "MGS")
        self.fs = ManagedFilesystem.objects.create(mgs = self.mgt, name = "testfs")
        self.mdt = ManagedMdt.create_for_volume(self._test_lun(self.host).id, filesystem = self.fs)
        self.ost = ManagedOst.create_for_volume(self._test_lun(self.host).id, filesystem = self.fs)
        if start:
            self.set_state(self.fs, 'available')
            self.mgt = freshen(self.mgt)
            self.fs = freshen(self.fs)
            self.mdt = freshen(self.mdt)
            self.ost = freshen(self.ost)
