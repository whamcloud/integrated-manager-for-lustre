from chroma_core.models.jobs import SchedulingError, Job, Command
from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem, ManagedHost
from chroma_core.services.job_scheduler.job_scheduler import RunJobThread, JobScheduler
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
import mock
from tests.unit.chroma_core.helper import JobTestCaseWithHost, MockAgentRpc, freshen
import datetime
import django.utils.timezone


class TestTransitionsWithCommands(JobTestCaseWithHost):
    def test_onejob(self):
        # Our self.host is initially lnet_up
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        # This tests a state transition which is done by a single job
        command_id = Command.set_state([(freshen(self.host), 'lnet_down')]).id
        self.assertEqual(Command.objects.get(pk = command_id).complete, True)
        self.assertEqual(Command.objects.get(pk = command_id).jobs.count(), 1)

        # Test that if I try to run the same again I get None
        command = Command.set_state([(freshen(self.host), 'lnet_down')])
        self.assertEqual(command, None)

    def test_2steps(self):
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        # This tests a state transition which requires two jobs acting on the same object
        command_id = Command.set_state([(freshen(self.host), 'lnet_unloaded')]).id
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_unloaded')
        self.assertEqual(Command.objects.get(pk = command_id).complete, True)
        self.assertEqual(Command.objects.get(pk = command_id).jobs.count(), 2)


class TestStateManager(JobTestCaseWithHost):
    def test_failing_job(self):
        mgt = ManagedMgs.create_for_volume(self._test_lun(self.host).id, name = "MGS")
        try:
            MockAgentRpc.succeed = False
            self.set_state(ManagedMgs.objects.get(pk = mgt.pk), 'mounted', check = False)
            # This is to check that the scheduler doesn't run past the failed job (like in HYD-1572)
            self.assertState(mgt, 'unformatted')
        finally:
            MockAgentRpc.succeed = True
            self.set_state(ManagedMgs.objects.get(pk = mgt.pk), 'mounted')

    def test_opportunistic_execution(self):
        # Set up an MGS, leave it offline
        mgt = ManagedMgs.create_for_volume(self._test_lun(self.host).id, name = "MGS")
        fs = ManagedFilesystem.objects.create(mgs = mgt, name = "testfs")
        ManagedMdt.create_for_volume(self._test_lun(self.host).id, filesystem = fs)
        ManagedOst.create_for_volume(self._test_lun(self.host).id, filesystem = fs)

        self.set_state(ManagedMgs.objects.get(pk = mgt.pk), 'unmounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unmounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version, 0)
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version_applied, 0)

        try:
            # Make it so that an MGS start operation will fail
            MockAgentRpc.succeed = False

            import chroma_core.lib.conf_param
            chroma_core.lib.conf_param.set_conf_params(fs, {"llite.max_cached_mb": "32"})

            self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version, 1)
            self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version_applied, 0)
        finally:
            MockAgentRpc.succeed = True

        self.set_state(fs, 'available')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'mounted')

        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version, 1)
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version_applied, 1)

    def test_invalid_state(self):
        with self.assertRaisesRegexp(SchedulingError, "is invalid for"):
            self.set_state(self.host, 'lnet_rhubarb')

    def test_1step(self):
        # Should be a simple one-step operation
        # Our self.host is initially lnet_up
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        # One job
        self.set_state(self.host, 'lnet_down')
        self.assertState(self.host, 'lnet_down')

        # One more job
        self.set_state(self.host, 'lnet_unloaded')
        self.assertState(self.host, 'lnet_unloaded')

    def test_completion_hook(self):
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')
        # This exercises the completion hooks (learning NIDs is a hook for lnet coming up)
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).lnetconfiguration.state, 'nids_known')

    def test_notification(self):
        """Test that state notifications cause the state of an object to change"""
        self.assertState(self.host, 'lnet_up')
        now = django.utils.timezone.now()
        JobSchedulerClient.notify(freshen(self.host), now, {'state': 'lnet_down'}, ['lnet_up'])
        self.assertEqual(freshen(self.host).state, 'lnet_down')

    def test_late_notification(self):
        """Test that notifications are droppped when they are older than
        the last change to an objects state"""
        self.assertState(self.host, 'lnet_up')
        awhile_ago = django.utils.timezone.now() - datetime.timedelta(seconds = 120)
        JobSchedulerClient.notify(freshen(self.host), awhile_ago, {'state': 'lnet_down'}, ['lnet_up'])
        self.assertEqual(freshen(self.host).state, 'lnet_up')

    def test_2steps(self):
        from chroma_core.models import ManagedHost
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        # This tests a state transition which requires two jobs acting on the same object
        self.set_state(self.host, 'lnet_unloaded')
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_unloaded')

    def test_cancel_pending(self):
        """Test cancelling a Job which is in state 'pending'"""

        self.set_state_delayed([(self.host, 'lnet_unloaded')])
        pending_jobs = Job.objects.filter(state = 'pending')

        # stop lnet, unload lnet
        self.assertEqual(pending_jobs.count(), 2)

        # This is the one we cancelled explicitly
        cancelled_job = pending_jobs[0]

        # This one should be cancelled as a result of cancelling it's dependency
        consequentially_cancelled_job = pending_jobs[1]

        JobSchedulerClient.cancel_job(pending_jobs[0].id)
        cancelled_job = freshen(cancelled_job)
        consequentially_cancelled_job = freshen(consequentially_cancelled_job)

        self.assertEqual(cancelled_job.state, 'complete')
        self.assertEqual(cancelled_job.errored, False)
        self.assertEqual(cancelled_job.cancelled, True)

        self.assertEqual(consequentially_cancelled_job.state, 'complete')
        self.assertEqual(consequentially_cancelled_job.errored, False)
        self.assertEqual(consequentially_cancelled_job.cancelled, True)

        pending_jobs = Job.objects.filter(state = 'pending')
        self.assertEqual(pending_jobs.count(), 0)

    def test_cancel_complete(self):
        """Test cancelling a Job which is in state 'complete': should be
        a no-op

        """
        self.set_state_delayed([(self.host, 'lnet_down')])
        job = Job.objects.get(state = 'pending')

        # Run, check that it goes to successful state
        self.set_state_complete()
        job = freshen(job)
        self.assertEqual(job.state, 'complete')
        self.assertEqual(job.cancelled, False)
        self.assertEqual(job.errored, False)

        # Try to cancel, check that it is not modified
        JobSchedulerClient.cancel_job(job.id)
        job = freshen(job)
        self.assertEqual(job.state, 'complete')
        self.assertEqual(job.cancelled, False)
        self.assertEqual(job.errored, False)

    def test_cancel_tasked(self):
        """Test that cancelling a Job which is in state 'tasked' involves
        calling the cancel method on RunJobThread"""

        cancel_bak = RunJobThread.cancel
        RunJobThread.cancel = mock.Mock()

        def spawn_job(job):
            thread = mock.Mock()
            self.job_scheduler._run_threads[job.id] = thread

        spawn_bak = JobScheduler._spawn_job
        JobScheduler._spawn_job = mock.Mock(side_effect=spawn_job)

        try:
            self.set_state_delayed([(self.host, 'lnet_down')])
            # Start our mock thread 'running'
            self.job_scheduler._run_next()
            job = Job.objects.get(state = 'tasked')
            JobSchedulerClient.cancel_job(job.id)
            # That call to cancel should have reached the thread
            self.assertEqual(self.job_scheduler._run_threads[job.id].cancel.call_count, 1)
        finally:
            RunJobThread.cancel = cancel_bak
            JobScheduler._spawn_job = spawn_bak
