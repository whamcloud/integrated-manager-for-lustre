from collections import defaultdict
from contextlib import contextmanager
import datetime
from chroma_agent.crypto import Crypto
from chroma_api.authentication import CsrfAuthentication
from chroma_core.lib.cache import ObjectCache
from chroma_core.services.http_agent import AgentSessionRpc
from chroma_core.services.https_frontend import RoutingProxyRpc, RoutingProxy
from chroma_core.services.job_scheduler.agent_rpc import AgentException, AgentRpc
from chroma_core.services.log import log_register
from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonRpcInterface
from chroma_core.services.http_agent import Service as HttpAgentService
from dateutil import tz
from django.test import TestCase
import mock
from chroma_core.models.jobs import Command
from chroma_core.models import Volume, VolumeNode, ManagedHost, LogMessage
from chroma_core.services.queue import ServiceQueue
from chroma_core.services.rpc import ServiceRpcInterface
import re
from tastypie.serializers import Serializer
from tests.unit.chroma_api.tastypie_test import TestApiClient


log = log_register('test_helper')


class FakeCrypto(Crypto):
    FOLDER = "/tmp/"


def freshen(obj):
    return obj.__class__.objects.get(pk=obj.pk)


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


class MockAgent(object):
    mock_servers = {}
    calls = []
    host_calls = defaultdict(list)

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

    def __init__(self, host, log = None, console_callback = None, timeout = None):
        self.host = host

    def _fail(self):
        log.error("Synthetic agent error on host %s" % self.host)
        raise AgentException(self.host.fqdn, "cmd", {'foo': 'bar'}, "Fake backtrace")

    def invoke(self, cmd, args = {}):
        self.calls.append((cmd, args))
        self.host_calls[self.host].append((cmd, args))

        if not self.succeed:
            self._fail()

        if (cmd, args) in self.fail_commands:
            self._fail()

        log.info("invoke_agent %s %s %s" % (self.host, cmd, args))
        if cmd == "lnet_scan":
            return self.mock_servers[self.host.address]['nids']
        elif cmd == 'host_properties':
            return {
                'time': datetime.datetime.utcnow().isoformat() + "Z",
                'fqdn': self.mock_servers[self.host.address]['fqdn'],
                'nodename': self.mock_servers[self.host.address]['nodename'],
                'capabilities': self.capabilities,
                'selinux_enabled': self.selinux_enabled,
                'agent_version': self.version,
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
            return self.mock_servers[self.host.address]['detect-scan']
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
                fqdn = self.mock_servers[self.host]['fqdn']
                csr = FakeCrypto().generate_csr(fqdn)
                response = api_client.post(args['url'] + "register/xyz/", data = {
                    'address': self.host,
                    'fqdn': fqdn,
                    'nodename': self.mock_servers[self.host]['nodename'],
                    'capabilities': ['manage_targets'],
                    'version': MockAgent.version,
                    'csr': csr
                })
                assert response.status_code == 201
                registration_data = Serializer().deserialize(response.content, format = response['Content-Type'])
                print "MockAgent.invoke returning %s" % registration_data
                return registration_data
            finally:
                CsrfAuthentication.is_authenticated = old_is_authenticated
        elif cmd == 'device_plugin':
            try:
                data = self.mock_servers[self.host.address]['device-plugin']
            except KeyError:
                data = {}
            if args['plugin'] in data:
                return {args['plugin']: data[args['plugin']]}
            else:
                raise AgentException(self.host.fqdn, cmd, args, "")


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
        initial_call_count = len(MockAgent.calls)
        yield
        wrapped_calls = MockAgent.calls[initial_call_count:]
        for cmd, args in wrapped_calls:
            if cmd == agent_command and args == agent_args:
                return
        raise self.failureException("Command '%s', %s was not invoked (calls were: %s)" % (agent_command, agent_args, wrapped_calls))

    def _test_lun(self, primary_host, *args):
        volume = Volume.objects.create()
        VolumeNode.objects.create(volume = volume, host = primary_host, path = "/fake/path/%s" % volume.id, primary = True)
        for host in args:
            VolumeNode.objects.create(volume = volume, host = host, path = "/fake/path/%s" % volume.id, primary = False)

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

        # NB by self stage celery has already read in its settings, so we have to update
        # ALWAYS_EAGER inside celery instead of in settings.*
        from celery.app import app_or_default
        self.old_celery_always_eager = app_or_default().conf.CELERY_ALWAYS_EAGER
        app_or_default().conf.CELERY_ALWAYS_EAGER = True
        self.old_celery_eager_propagates_exceptions = app_or_default().conf.CELERY_EAGER_PROPAGATES_EXCEPTIONS
        app_or_default().conf.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        # Intercept attempts to call out to lustre servers
        import chroma_core.services.job_scheduler.agent_rpc
        self.old_agent = chroma_core.services.job_scheduler.agent_rpc.Agent
        self.old_agent_ssh = chroma_core.services.job_scheduler.agent_rpc.AgentSsh
        MockAgent.mock_servers = self.mock_servers

        class MockAgentRpc(AgentRpc):
            @classmethod
            def remove(cls, fqdn):
                pass

        chroma_core.services.job_scheduler.agent_rpc.AgentRpc = MockAgentRpc
        chroma_core.services.job_scheduler.agent_rpc.Agent = MockAgent
        chroma_core.services.job_scheduler.agent_rpc.AgentSsh = MockAgent

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

        patch_daemon_rpc(RoutingProxyRpc, RoutingProxy(None))

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
                VolumeNode.delete(vn.id)
            for volume in Volume.objects.all():
                if volume.volumenode_set.count() == 0:
                    Volume.delete(volume.id)

        AgentDaemonRpcInterface.remove_host_resources = mock.Mock(side_effect = fake_remove_host_resources)

    def tearDown(self):
        import chroma_core.services.job_scheduler.agent_rpc
        chroma_core.services.job_scheduler.agent_rpc.Agent = self.old_agent
        chroma_core.services.job_scheduler.agent_rpc.AgentSsh = self.old_agent_ssh

        from celery.app import app_or_default
        app_or_default().conf.CELERY_ALWAYS_EAGER = self.old_celery_always_eager
        app_or_default().conf.CELERY_ALWAYS_EAGER = self.old_celery_eager_propagates_exceptions


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
