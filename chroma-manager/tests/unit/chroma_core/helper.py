from collections import defaultdict
from contextlib import contextmanager
import datetime
from chroma_core.services.job_scheduler.job_scheduler import SerializedCalls
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
            return {'uuid': uuid.uuid1().__str__(), 'inode_count': 666, 'inode_size': 777}
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
        elif cmdline == "device-plugin":
            return {

            }
        elif cmdline == "device-plugin --plugin=lustre":
            return {'lustre': {
                'lnet_up': True,
                'lnet_loaded': True
            }}


def run_next():
    from chroma_core.models.jobs import Job

    while True:
        runnable_jobs = Job.get_ready_jobs()
        if not runnable_jobs:
            break

        log.info("run_next: %d runnable jobs of (%d pending, %d tasked)" % (
            len(runnable_jobs),
            Job.objects.filter(state = 'pending').count(),
            Job.objects.filter(state = 'tasked').count()))

        for job in runnable_jobs:
            start_job(job)


def complete_job(job, errored = False, cancelled = False):
    from chroma_core.models.jobs import StateChangeJob
    from chroma_core.lib.job import job_log
    success = not (errored or cancelled)
    if success and isinstance(job, StateChangeJob):
        new_state = job.state_transition[2]
        obj = job.get_stateful_object()
        obj.set_state(new_state, intentional = True)
        job_log.info("Job %d: StateChangeJob complete, setting state %s on %s" % (job.pk, new_state, obj))

    job_log.info("Job %s completing (errored=%s, cancelled=%s)" %
                 (job.id, errored, cancelled))
    job.state = 'completing'
    job.errored = errored
    job.cancelled = cancelled
    job.save()

    SerializedCalls.call('complete_job', job.pk)


def start_job(job):
    from chroma_core.services.job_scheduler.job_scheduler import RunJobThread
    import sys
    import traceback

    log.info("Job %d: Job.run %s" % (job.id, job.description()))
    # Important: multiple connections are allowed to call run() on a job
    # that they see as pending, but only one is allowed to proceed past this
    # point and spawn tasks.

    # All the complexity of StateManager's dependency calculation doesn't
    # matter here: we've reached our point in the queue, all I need to check now
    # is - are this Job's immediate dependencies satisfied?  And are any deps
    # for a statefulobject's new state satisfied?  If so, continue.  If not, cancel.

    try:
        deps_satisfied = job._deps_satisfied()
    except Exception:
        # Catchall exception handler to ensure progression even if Job
        # subclasses have bugs in their get_deps etc.
        log.error("Job %s: exception in dependency check: %s" % (job.id,
                                                                     '\n'.join(traceback.format_exception(*(sys.exc_info())))))
        complete_job(job, cancelled = True)
        return

    if not deps_satisfied:
        log.warning("Job %d: cancelling because of failed dependency" % job.id)
        complete_job(job, cancelled = True)
        # TODO: tell someone WHICH dependency
        return

    job.state = 'tasked'
    job.save()
    RunJobThread(job.id).run()


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

    def set_state(self, obj, state, check = True):
        Command.set_state([(obj, state)], "Unit test transition %s to %s" % (obj, state))
        if check:
            try:
                self.assertState(obj, state)
            except obj.__class__.DoesNotExist:
                pass

    def assertState(self, obj, state):
        self.assertEqual(freshen(obj).state, state)

    def setUp(self):
        # FIXME: have to do this before every test because otherwise
        # one test will get all the setup of StoragePluginClass records,
        # the in-memory instance of storage_plugin_manager will expect
        # them to still be there but they'll have been cleaned
        # out of the database.  Setting up this stuff should be done
        # as part of the initial DB setup before any test is started
        # so that it's part of the baseline that's rolled back to
        # after each test.
        import chroma_core.lib.storage_plugin.manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = chroma_core.lib.storage_plugin.manager.StoragePluginManager()

        # NB by this stage celery has already read in its settings, so we have to update
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
        # turn into local calls -- this is a catch-all to prevent any RPC classes
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

        from chroma_core.services.job_scheduler import JobScheduler
        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerRpcInterface
        patch_daemon_rpc(JobSchedulerRpcInterface, JobScheduler())

        import chroma_core.services.job_scheduler.job_scheduler
        chroma_core.services.job_scheduler.job_scheduler.start_job = mock.Mock(side_effect=start_job)
        chroma_core.services.job_scheduler.job_scheduler.complete_job = mock.Mock(side_effect=complete_job)
        chroma_core.services.job_scheduler.job_scheduler.run_next = mock.Mock(side_effect=run_next)

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
