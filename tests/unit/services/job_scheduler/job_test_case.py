import json
import mock
from contextlib import contextmanager
from itertools import chain

from chroma_core.lib.cache import ObjectCache
from chroma_core.models import Command
from chroma_core.models import ManagedTarget
from chroma_core.models import Nid
from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonRpcInterface
from chroma_core.services.queue import ServiceQueue
from chroma_core.services.rpc import ServiceRpcInterface
from tests.unit.chroma_core.helpers import MockAgentRpc, synthetic_volume_full, freshen
from tests.unit.chroma_core.helpers import (
    MockAgentSsh,
    create_simple_fs,
    log,
    load_default_profile,
    synthetic_host,
    parse_synthentic_device_info,
)
from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase


class JobTestCase(IMLUnitTestCase):
    mock_servers = None
    hosts = None

    @contextmanager
    def assertInvokes(self, agent_command, agent_args):
        initial_call_count = len(MockAgentRpc.calls)
        yield
        wrapped_calls = MockAgentRpc.calls[initial_call_count:]
        for cmd, args in wrapped_calls:
            if cmd == agent_command and args == agent_args:
                return
        raise self.failureException(
            "Command '%s', %s was not invoked (calls were: %s)" % (agent_command, agent_args, wrapped_calls)
        )

    def _test_lun(self, primary_host, secondary_hosts=None):
        return synthetic_volume_full(primary_host, secondary_hosts)

    def _synthetic_host_with_nids(self, address):
        return synthetic_host(address, self.mock_servers[address]["nids"])

    ###
    # set_and_assert_state
    #
    # Bit weird because if you say check = True then the state is set and asserted and the updated
    # object is returned, but if check = False then it returns the command that is going to change the
    # state
    #
    def set_and_assert_state(self, obj, state, check=True, run=True):
        command = Command.set_state([(obj, state)], "Unit test transition %s to %s" % (obj, state), run=run)
        log.debug("calling drain_progress")
        self.drain_progress()
        if check:
            if command:
                self.assertEqual(Command.objects.get(pk=command.id).complete, True)
            try:
                return self.assertState(obj, state)
            except obj.__class__.DoesNotExist:
                return obj
        else:
            return command

    def set_state_delayed(self, obj_state_pairs):
        """Schedule some jobs without executing them"""
        Command.set_state(obj_state_pairs, "Unit test transition", run=False)

    def set_state_complete(self):
        """Run any outstanding jobs"""
        self.job_scheduler._run_next()
        self.assertEqual(Command.objects.filter(complete=False).count(), 0)

    def assertState(self, obj, state):
        obj = freshen(obj)
        self.assertEqual(obj.state, state)
        return obj

    def drain_progress(self, skip_advance=False):
        while not self.job_scheduler.progress.empty():
            msg = self.job_scheduler.progress.get_nowait()
            if msg[0] == "advance" and skip_advance:
                continue
            self.job_scheduler.progress._handle(msg)

    @classmethod
    def setUpTestData(cls):
        load_default_profile()

    def setUp(self):
        super(JobTestCase, self).setUp()

        from chroma_core.services.http_agent import HttpAgentRpc
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

        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = (
            chroma_core.lib.storage_plugin.manager.StoragePluginManager()
        )

        # Intercept attempts to call out to lustre servers
        import chroma_core.services.job_scheduler.agent_rpc

        self.old_agent_rpc = chroma_core.services.job_scheduler.agent_rpc.AgentRpc
        self.old_agent_ssh = chroma_core.services.job_scheduler.agent_rpc.AgentSsh
        MockAgentRpc.mock_servers = self.mock_servers
        MockAgentSsh.mock_servers = self.mock_servers

        chroma_core.services.job_scheduler.agent_rpc.AgentRpc = MockAgentRpc
        chroma_core.services.job_scheduler.agent_rpc.AgentSsh = MockAgentSsh

        # Any RPCs that are going to get called need explicitly overriding to
        # turn into local calls -- self is a catch-all to prevent any RPC classes
        # from trying to do network comms during unit tests
        ServiceRpcInterface._call = mock.Mock(side_effect=NotImplementedError)
        ServiceQueue.put = mock.Mock()
        ServiceQueue.purge = mock.Mock()

        # Create an instance for the purposes of the test
        from chroma_core.services.plugin_runner.resource_manager import ResourceManager

        resource_manager = ResourceManager()
        from chroma_core.services.plugin_runner import AgentPluginHandlerCollection

        def patch_daemon_rpc(rpc_class, test_daemon):
            # Patch AgentDaemonRpc to call our instance instead of trying to do an RPC
            def rpc_local(fn_name, *args, **kwargs):
                # Run the response through a serialize/deserialize cycle to
                # give it that special RPC flavor.
                retval = json.loads(json.dumps(getattr(test_daemon, fn_name)(*args, **kwargs)))
                log.info("patch_daemon_rpc: %s(%s %s) -> %s" % (fn_name, args, kwargs, retval))
                return retval

            rpc_class._call = mock.Mock(side_effect=rpc_local)

        aphc = AgentPluginHandlerCollection(resource_manager)

        patch_daemon_rpc(AgentDaemonRpcInterface, aphc)

        aphc.update_host_resources = mock.Mock(side_effect=parse_synthentic_device_info)

        patch_daemon_rpc(HttpAgentRpc, HttpAgentService())

        from chroma_core.services.job_scheduler.dep_cache import DepCache
        from chroma_core.services.job_scheduler.job_scheduler import JobScheduler, RunJobThread
        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerRpc
        from chroma_core.services.job_scheduler.job_scheduler_notify import NotificationQueue

        ObjectCache.clear()
        self.job_scheduler = JobScheduler()
        patch_daemon_rpc(JobSchedulerRpc, self.job_scheduler)

        # self.job_scheduler.progress.put = mock.Mock(side_effect = lambda msg: self.job_scheduler.progress._handle(msg))
        # self.job_scheduler.progress.advance = mock.Mock(side_effect = lambda msg: self.job_scheduler.progress._handle(msg))

        from chroma_core.services.job_scheduler import QueueHandler

        job_scheduler_queue_handler = QueueHandler(self.job_scheduler)

        def job_scheduler_queue_immediate(body):
            log.info("job_scheduler_queue_immediate: %s" % body)
            job_scheduler_queue_handler.on_message(body)

        NotificationQueue.put = mock.Mock(side_effect=job_scheduler_queue_immediate)

        import chroma_core.services.job_scheduler.job_scheduler

        chroma_core.services.job_scheduler.job_scheduler._disable_database = mock.Mock()

        def _spawn_job(job):
            log.debug("functional spawn job")
            thread = RunJobThread(self.job_scheduler.progress, self.job_scheduler._db_quota, job, job.get_steps())
            self.job_scheduler._run_threads[job.id] = thread
            thread._run()

        self.job_scheduler._spawn_job = mock.Mock(side_effect=_spawn_job)

        def run_next():
            while True:
                runnable_jobs = self.job_scheduler._job_collection.ready_jobs

                log.info(
                    "run_next: %d runnable jobs of (%d pending, %d tasked)"
                    % (
                        len(runnable_jobs),
                        len(self.job_scheduler._job_collection.pending_jobs),
                        len(self.job_scheduler._job_collection.tasked_jobs),
                    )
                )

                if not runnable_jobs:
                    break

                dep_cache = DepCache()
                ok_jobs, cancel_jobs = self.job_scheduler._check_jobs(runnable_jobs, dep_cache)
                self.job_scheduler._job_collection.update_many(ok_jobs, "tasked")
                for job in cancel_jobs:
                    self.job_scheduler._complete_job(job, False, True)
                for job in ok_jobs:
                    self.job_scheduler._spawn_job(job)

                self.drain_progress(skip_advance=True)

        JobScheduler._run_next = mock.Mock(side_effect=run_next)
        #
        # def complete_job(job, errored = False, cancelled = False):
        #     ObjectCache.clear()
        #     self.job_scheduler._complete_job(job, errored, cancelled)

        # JobScheduler.complete_job = mock.Mock(side_effect=complete_job)

        # Patch host removal because we use a _test_lun function that generates Volumes
        # with no corresponding StorageResourceRecords, so the real implementation wouldn't
        # remove them
        def fake_remove_host_resources(host_id):
            from chroma_core.models.host import Volume, VolumeNode

            for vn in VolumeNode.objects.filter(host__id=host_id):
                vn.mark_deleted()
            for volume in Volume.objects.all():
                if volume.volumenode_set.count() == 0:
                    volume.mark_deleted()

        AgentDaemonRpcInterface.remove_host_resources = mock.Mock(side_effect=fake_remove_host_resources)

        def get_targets_fn():
            from chroma_core.models import ManagedHost

            ids = [x.id for x in ManagedHost.objects.all()]
            host_id = ids[0]

            return [
                {"name": "MGS", "active_host_id": host_id, "host_ids": ids, "uuid": "uuid_mgt"},
                {"name": "testfs-MDT0000", "active_host_id": host_id, "host_ids": ids, "uuid": "uuid_mdt"},
                {"name": "testfs-OST0000", "active_host_id": host_id, "host_ids": ids, "uuid": "uuid_ost0"},
                {"name": "testfs-OST0001", "active_host_id": host_id, "host_ids": ids, "uuid": "uuid_ost1"},
                {"name": "testfs2-OST0000", "active_host_id": host_id, "host_ids": ids, "uuid": "uuid_fs2_ost0"},
                {"name": "testfs2-MDT0000", "active_host_id": host_id, "host_ids": ids, "uuid": "uuid_fs2_mdt"},
            ]

        self.get_targets_mock = mock.MagicMock(side_effect=get_targets_fn)
        mock.patch("chroma_core.lib.graphql.get_targets", new=self.get_targets_mock).start()

        self.invoke_rust_agent_mock = mock.MagicMock(return_value='{"Ok": ""}')
        mock.patch("chroma_core.lib.job.invoke_rust_agent", new=self.invoke_rust_agent_mock).start()

        self.addCleanup(mock.patch.stopall)

    def tearDown(self):
        import chroma_core.services.job_scheduler.agent_rpc

        chroma_core.services.job_scheduler.agent_rpc.AgentRpc = self.old_agent_rpc
        chroma_core.services.job_scheduler.agent_rpc.AgentSsh = self.old_agent_ssh

    def create_simple_filesystem(self, start=True):
        (mgt, fs, mdt, ost) = create_simple_fs()

        self.fs = fs
        self.mgt = mgt
        self.mdt = mdt
        self.ost = ost

        if start:
            self.fs = self.set_and_assert_state(self.fs, "available")


class JobTestCaseWithHost(JobTestCase):
    mock_servers = {
        "myaddress": {
            "fqdn": "myaddress.mycompany.com",
            "nodename": "test01.myaddress.mycompany.com",
            "nids": [Nid.Nid("192.168.0.1", "tcp", 0)],
        }
    }

    @classmethod
    def setUpTestData(cls):
        super(JobTestCaseWithHost, cls).setUpTestData()

        cls.hosts = []
        for address, info in cls.mock_servers.items():
            host = synthetic_host(address=address, fqdn=info["fqdn"], nids=info["nids"], nodename=info["nodename"])
            cls.hosts.append(host)

    def setUp(self):
        super(JobTestCaseWithHost, self).setUp()

        for host in self.hosts:
            host.refresh_from_db()

        # Handy if you're only using one
        self.host = self.hosts[0]
