from collections import defaultdict
from contextlib import contextmanager
import datetime
from chroma_core.lib.cache import ObjectCache
from chroma_core.services.log import log_register
from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonRpcInterface, AgentDaemonQueue
from django.test import TestCase
import mock
from chroma_core.lib.agent import AgentException
from chroma_core.models.jobs import Command
from chroma_core.models import Volume, VolumeNode
from chroma_core.services.queue import ServiceQueue
from chroma_core.services.rpc import ServiceRpcInterface


log = log_register('test_helper')


def freshen(obj):
    return obj.__class__.objects.get(pk=obj.pk)


class MockAgent(object):
    label_counter = 0
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
    fail_globs = []

    def __init__(self, host, log = None, console_callback = None, timeout = None):
        self.host = host

    def _fail(self):
        log.error("Synthetic agent error on host %s" % self.host)
        raise AgentException(self.host.id, agent_exception = RuntimeError("Fake exception"), agent_backtrace = "Fake backtrace")

    def invoke(self, cmdline, args = None):
        self.calls.append((cmdline, args))
        self.host_calls[self.host].append((cmdline, args))

        if not self.succeed:
            self._fail()

        if cmdline in self.fail_globs:
            self._fail()

        log.info("invoke_agent %s %s %s" % (self.host, cmdline, args))
        if cmdline == "lnet-scan":
            return self.mock_servers[self.host.address]['nids']
        elif cmdline == 'host-properties':
            return {
                'time': datetime.datetime.utcnow().isoformat() + "Z",
                'fqdn': self.mock_servers[self.host.address]['fqdn'],
                'nodename': self.mock_servers[self.host.address]['nodename'],
                'capabilities': ['manage_targets']
            }
        elif cmdline.startswith("format-target"):
            import uuid
            import re
            inode_size = None
            if 'mkfsoptions' in args:
                inode_arg = re.search("-I (\d+)", args['mkfsoptions'])
                if inode_arg:
                    inode_size = int(inode_arg.group(1).__str__())

            if inode_size is None:
                # A 'foo' value
                inode_size = 777

            return {'uuid': uuid.uuid1().__str__(), 'inode_count': 666, 'inode_size': inode_size}
        elif cmdline.startswith('stop-target'):
            import re
            from chroma_core.models import ManagedTarget
            ha_label = re.search("--ha_label ([^\s]+)", cmdline).group(1)
            target = ManagedTarget.objects.get(ha_label = ha_label)
            return
        elif cmdline.startswith('start-target'):
            import re
            from chroma_core.models import ManagedTarget
            ha_label = re.search("--ha_label ([^\s]+)", cmdline).group(1)
            target = ManagedTarget.objects.get(ha_label = ha_label)
            return {'location': target.primary_server().nodename}
        elif cmdline.startswith('register-target'):
            import re

            # generic target (should be future-proof for multiple MDTs)
            tgt_match = re.search("--mountpoint /mnt/(\w+)/(.{3})(\d+)", cmdline)
            if tgt_match:
                fsname, kind, idx = tgt_match.groups()
                return {'label': "%s-%s%04d" % (fsname, kind.upper(), int(idx))}

            # special-case match for non-CMD MDTs
            mdt_match = re.search("--mountpoint /mnt/(\w+)/mdt", cmdline)
            if mdt_match:
                return {'label': "%s-MDT0000" % mdt_match.group(1)}

            # fallback, gin up a label
            MockAgent.label_counter += 1
            return {'label': "foofs-TTT%04d" % self.label_counter}
        elif cmdline.startswith('detect-scan'):
            return self.mock_servers[self.host.address]['detect-scan']
        elif cmdline == "device-plugin --plugin=lustre":
            return {'lustre': {
                'lnet_up': True,
                'lnet_loaded': True
            }}
        elif cmdline.startswith("device-plugin"):
            try:
                return self.mock_servers[self.host.address]['device-plugin']
            except KeyError:
                return {}


class JobTestCase(TestCase):
    mock_servers = None
    hosts = None

    @contextmanager
    def assertInvokes(self, agent_command):
        initial_call_count = len(MockAgent.calls)
        yield
        wrapped_calls = MockAgent.calls[initial_call_count:]
        for call in wrapped_calls:
            call_cmd = call[0]
            if call_cmd == agent_command:
                return
        raise self.failureException("Command '%s' was not invoked (calls were: %s)" % (agent_command, wrapped_calls))

    def _test_lun(self, primary_host, *args):
        volume = Volume.objects.create()
        VolumeNode.objects.create(volume = volume, host = primary_host, path = "/fake/path/%s" % volume.id, primary = True)
        for host in args:
            VolumeNode.objects.create(volume = volume, host = host, path = "/fake/path/%s" % volume.id, primary = False)

        return volume

    def set_state(self, obj, state, check = True, run = True):
        Command.set_state([(obj, state)], "Unit test transition %s to %s" % (obj, state), run = run)
        if check:
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
        import chroma_core.lib.agent
        self.old_agent = chroma_core.lib.agent.Agent
        MockAgent.mock_servers = self.mock_servers
        chroma_core.lib.agent.Agent = MockAgent

        # Any RPCs that are going to get called need explicitly overriding to
        # turn into local calls -- self is a catch-all to prevent any RPC classes
        # from trying to do network comms during unit tests
        ServiceRpcInterface._call = mock.Mock(side_effect = NotImplementedError)
        ServiceQueue.put = mock.Mock(side_effect = NotImplementedError)

        # Create an instance for the purposes of the test
        from chroma_core.services.plugin_runner.agent_daemon import AgentDaemon
        agent_daemon = AgentDaemon()

        def patch_daemon_rpc(rpc_class, test_daemon):
            # Patch AgentDaemonRpc to call our instance instead of trying to do an RPC
            def rpc_local(fn_name, *args, **kwargs):
                retval = getattr(test_daemon, fn_name)(*args, **kwargs)
                log.info("patch_daemon_rpc: %s(%s %s) -> %s" % (fn_name, args, kwargs, retval))
                return retval

            rpc_class._call = mock.Mock(side_effect = rpc_local)

        patch_daemon_rpc(AgentDaemonRpcInterface, agent_daemon)

        # When someone pushes something to 'agent' queue, call back AgentDaemon
        def queue_immediate(body):
            log.info("patch_daemon_queue: %s" % body)
            agent_daemon.on_message(body)
        AgentDaemonQueue.put = mock.Mock(side_effect = queue_immediate)

        from chroma_core.services.job_scheduler.dep_cache import DepCache
        from chroma_core.services.job_scheduler.job_scheduler import JobScheduler, RunJobThread
        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerRpcInterface, ModificationNotificationQueue
        self.job_scheduler = JobScheduler()
        patch_daemon_rpc(JobSchedulerRpcInterface, self.job_scheduler)

        from chroma_core.services.job_scheduler import QueueHandler
        job_scheduler_queue_handler = QueueHandler(self.job_scheduler)

        def job_scheduler_queue_immediate(body):
            log.info("job_scheduler_queue_immediate: %s" % body)
            job_scheduler_queue_handler.on_message(body)
        ModificationNotificationQueue.put = mock.Mock(side_effect = job_scheduler_queue_immediate)

        def spawn_job(job):
            RunJobThread(self.job_scheduler, job).run()

        JobScheduler._spawn_job = mock.Mock(side_effect=spawn_job)

        def run_next():
            from chroma_core.models.jobs import Job

            while True:
                runnable_jobs = Job.get_ready_jobs()

                log.info("run_next: %d runnable jobs of (%d pending, %d tasked)" % (
                    len(runnable_jobs),
                    Job.objects.filter(state = 'pending').count(),
                    Job.objects.filter(state = 'tasked').count()))

                if not runnable_jobs:
                    break

                dep_cache = DepCache()
                for job in runnable_jobs:
                    self.job_scheduler._start_job(job, dep_cache)

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
        import chroma_core.lib.agent
        chroma_core.lib.agent.Agent = self.old_agent

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
        self.hosts = [ManagedHost.create_from_string(address)[0] for address, info in self.mock_servers.items()]

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
