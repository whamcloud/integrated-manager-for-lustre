import datetime

import mock
import django.utils.timezone

from chroma_core.lib.cache import ObjectCache
from chroma_core.models.jobs import SchedulingError, Job
from chroma_core.models.command import Command
from chroma_core.models import ManagedMgs, ManagedTarget
from chroma_core.models import LNetConfiguration
from chroma_core.services.job_scheduler.job_scheduler import RunJobThread
from chroma_core.services.job_scheduler import job_scheduler_notify
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from tests.unit.chroma_core.helpers import freshen
from tests.unit.chroma_core.helpers import MockAgentRpc
from tests.unit.services.job_scheduler.job_test_case import JobTestCaseWithHost
from chroma_api.urls import api


class TestTransitionsWithCommands(JobTestCaseWithHost):
    def setUp(self):
        super(TestTransitionsWithCommands, self).setUp()

        self.lnet_configuration = self.host.lnet_configuration

    def test_onejob(self):
        # Our self.host is initially lnet_up
        self.assertEqual(LNetConfiguration.objects.get(pk=self.lnet_configuration.pk).state, "lnet_up")

        # This tests a state transition which is done by a single job
        command_id = JobSchedulerClient.command_run_jobs(
            [{"class_name": "UpdateDevicesJob", "args": {}}], "Test single job action"
        )
        self.drain_progress()

        self.assertEqual(Command.objects.get(pk=command_id).complete, True)
        self.assertEqual(Command.objects.get(pk=command_id).jobs.count(), 1)

        # Test that if I try to run the same again I get None
        command = Command.set_state([(freshen(self.lnet_configuration), "lnet_up")])
        self.assertEqual(command, None)

    def test_2steps(self):
        self.assertEqual(LNetConfiguration.objects.get(pk=self.lnet_configuration.pk).state, "lnet_up")

        # This tests a state transition which requires two jobs acting on the same object
        # lnet_up -> lnet_down issues an StopLNetJob and a UnloadLNetJob
        command_id = Command.set_state([(freshen(self.lnet_configuration), "lnet_unloaded")]).id
        self.drain_progress()

        self.assertEqual(LNetConfiguration.objects.get(pk=self.lnet_configuration.pk).state, "lnet_unloaded")
        self.assertEqual(Command.objects.get(pk=command_id).complete, True)
        self.assertEqual(Command.objects.get(pk=command_id).jobs.count(), 2)


class TestStateManager(JobTestCaseWithHost):
    def setUp(self):
        super(TestStateManager, self).setUp()
        self.lnet_configuration = self.host.lnet_configuration
        self._completion_hook_count = 0
        self.job_scheduler.add_completion_hook(self._completion_hook)

    def tearDown(self):
        super(TestStateManager, self).tearDown()
        self.job_scheduler.del_completion_hook(self._completion_hook)

    def _completion_hook(self, changed_item, command, updated_attrs):
        self._completion_hook_count += 1

    def test_failing_job(self):
        mgt, tms = ManagedMgs.create_for_volume(self._test_lun(self.host).id, name="MGS")
        ObjectCache.add(ManagedTarget, mgt.managedtarget_ptr)

        try:
            MockAgentRpc.succeed = False
            # This is to check that the scheduler doesn't run past the failed job (like in HYD-1572)
            self.set_and_assert_state(mgt.managedtarget_ptr, "mounted", check=False)
            mgt = self.assertState(mgt, "unformatted")
        finally:
            MockAgentRpc.succeed = True
            mgt.managedtarget_ptr = self.set_and_assert_state(mgt.managedtarget_ptr, "mounted")

    def test_opportunistic_execution(self):
        # Set up an MGS, leave it offline
        self.create_simple_filesystem(self.host)

        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "unmounted")
        self.fs = self.assertState(self.fs, "unavailable")
        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).conf_param_version, 0)
        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).conf_param_version_applied, 0)

        try:
            # Make it so that an MGS start operation will fail
            MockAgentRpc.succeed = False

            import chroma_core.lib.conf_param

            chroma_core.lib.conf_param.set_conf_params(self.fs, {"llite.max_cached_mb": "32"})

            self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).conf_param_version, 1)
            self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).conf_param_version_applied, 0)
        finally:
            MockAgentRpc.succeed = True

        self.fs = self.set_and_assert_state(self.fs, "available")
        self.mgt = self.assertState(self.mgt, "mounted")

        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).conf_param_version, 1)
        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).conf_param_version_applied, 1)

    def test_invalid_state(self):
        with self.assertRaisesRegexp(SchedulingError, "is invalid for"):
            self.host = self.set_and_assert_state(self.host, "lnet_rhubarb")

    def test_1step(self):
        # Should be a simple one-step operation
        # Our self.host is initially lnet_up
        self.assertEqual(LNetConfiguration.objects.get(pk=self.lnet_configuration.pk).state, "lnet_up")

        # One job
        self.lnet_configuration = self.set_and_assert_state(self.lnet_configuration, "lnet_down")

        # One more job
        self.lnet_configuration = self.set_and_assert_state(self.lnet_configuration, "lnet_unloaded")

    def test_completion_hook(self):
        self.assertEqual(self.lnet_configuration.state, "lnet_up")
        # This exercises the completion hooks
        for x in range(10):
            self.lnet_configuration = self.set_and_assert_state(
                self.lnet_configuration, "lnet_unloaded"
            )  # +2 _completion_hook_count
            self.lnet_configuration = self.set_and_assert_state(
                self.lnet_configuration, "lnet_down"
            )  # +1 _completion_hook_count
            self.lnet_configuration = self.set_and_assert_state(
                self.lnet_configuration, "lnet_up"
            )  # +1 _completion_hook_count
            self.assertEqual(self._completion_hook_count, ((x + 1) * 4))

    def test_notification(self):
        """Test that state notifications cause the state of an object to change"""
        self.lnet_configuration = self.assertState(self.lnet_configuration, "lnet_up")
        now = django.utils.timezone.now()
        job_scheduler_notify.notify(freshen(self.lnet_configuration), now, {"state": "lnet_down"}, ["lnet_up"])
        self.assertEqual(freshen(self.lnet_configuration).state, "lnet_down")

    def test_late_notification(self):
        """Test that notifications are droppped when they are older than
        the last change to an objects state"""
        self.lnet_configuration = self.assertState(self.lnet_configuration, "lnet_up")
        awhile_ago = django.utils.timezone.now() - datetime.timedelta(seconds=120)
        job_scheduler_notify.notify(freshen(self.lnet_configuration), awhile_ago, {"state": "lnet_down"}, ["lnet_up"])
        self.assertEqual(freshen(self.lnet_configuration).state, "lnet_up")

    def test_buffered_notification(self):
        """Test that notifications for locked items are buffered and
        replayed when the locking Job has completed."""
        self.lnet_configuration = self.assertState(self.lnet_configuration, "lnet_up")

        # Set boot_time to something that should change.
        now = django.utils.timezone.now()
        job_scheduler_notify.notify(freshen(self.host), now, {"boot_time": now})
        self.assertEqual(freshen(self.host).boot_time, now)

        # Not much later, but later enough (fastest boot EVAR).
        later = django.utils.timezone.now()
        self.assertNotEqual(later, now)

        # This is more direct than fooling around with trying to get the
        # timing right. Contrive a locking event on the host we want to
        # notify, and the notification should be buffered.
        self.job_scheduler._lock_cache.all_by_item[self.host] = ["fake lock"]
        job_scheduler_notify.notify(freshen(self.host), later, {"boot_time": later})

        # Now, remove the lock and make sure that the second notification
        # didn't get through during the lock.
        del self.job_scheduler._lock_cache.all_by_item[self.host]
        self.assertEqual(freshen(self.host).boot_time, now)

        # Run any job, doesn't matter -- we just want to ensure that the
        # notification buffer is drained after the job completes.
        self.lnet_configuration = self.set_and_assert_state(self.lnet_configuration, "lnet_down")
        self.assertEqual(freshen(self.host).boot_time, later)

        # Just for completeness, check that the notification buffer for this
        # host was completely drained and removed.
        buffer_key = (tuple(self.host.content_type.natural_key()), self.host.pk)
        self.assertEqual([], self.job_scheduler._notification_buffer.drain_notifications_for_key(buffer_key))
        self.assertEqual([], self.job_scheduler._notification_buffer.notification_keys)

    def test_2steps(self):
        self.assertEqual(LNetConfiguration.objects.get(pk=self.lnet_configuration.pk).state, "lnet_up")

        # This tests a state transition which requires two jobs acting on the same object
        self.lnet_configuration = self.set_and_assert_state(self.lnet_configuration, "lnet_unloaded")

    def test_cancel_pending(self):
        """Test cancelling a Job which is in state 'pending'"""

        self.set_state_delayed([(self.host.lnet_configuration, "lnet_unloaded")])
        pending_jobs = Job.objects.filter(state="pending")

        # stop lnet, unload lnet
        self.assertEqual(pending_jobs.count(), 2)

        # This is the one we cancelled explicitly
        cancelled_job = pending_jobs[0]

        # This one should be cancelled as a result of cancelling it's dependency
        consequentially_cancelled_job = pending_jobs[1]

        JobSchedulerClient.cancel_job(pending_jobs[0].id)
        self.drain_progress()
        cancelled_job = freshen(cancelled_job)
        consequentially_cancelled_job = freshen(consequentially_cancelled_job)

        self.assertEqual(cancelled_job.state, "complete")
        self.assertEqual(cancelled_job.errored, False)
        self.assertEqual(cancelled_job.cancelled, True)

        self.assertEqual(consequentially_cancelled_job.state, "complete")
        self.assertEqual(consequentially_cancelled_job.errored, False)
        self.assertEqual(consequentially_cancelled_job.cancelled, True)

        pending_jobs = Job.objects.filter(state="pending")
        self.assertEqual(pending_jobs.count(), 0)
        self.assertFalse(self.job_scheduler._lock_cache.get_by_job(cancelled_job))

    def test_cancel_complete(self):
        """Test cancelling a Job which is in state 'complete': should be
        a no-op

        """
        self.set_state_delayed([(self.lnet_configuration, "lnet_down")])
        job = Job.objects.get(state="pending")

        # Run, check that it goes to successful state
        self.set_state_complete()
        job = freshen(job)
        self.assertEqual(job.state, "complete")
        self.assertEqual(job.cancelled, False)
        self.assertEqual(job.errored, False)

        # Try to cancel, check that it is not modified
        JobSchedulerClient.cancel_job(job.id)
        job = freshen(job)
        self.assertEqual(job.state, "complete")
        self.assertEqual(job.cancelled, False)
        self.assertEqual(job.errored, False)
        self.assertFalse(self.job_scheduler._lock_cache.get_by_job(job))

    def test_cancel_tasked(self):
        """Test that cancelling a Job which is in state 'tasked' involves
        calling the cancel method on RunJobThread"""

        cancel_bak = RunJobThread.cancel
        RunJobThread.cancel = mock.Mock()

        from tests.unit.chroma_core.helpers import log

        def spawn_job(job):
            log.debug("neutered spawn_job")
            thread = mock.Mock()
            self.job_scheduler._run_threads[job.id] = thread

        spawn_bak = JobScheduler._spawn_job
        self.job_scheduler._spawn_job = mock.Mock(side_effect=spawn_job)

        try:
            self.set_state_delayed([(self.lnet_configuration, "lnet_down")])
            # Start our mock thread 'running'
            self.job_scheduler._run_next()
            job = Job.objects.get(state="tasked")
            JobSchedulerClient.cancel_job(job.id)
            # That call to cancel should have reached the thread
            self.assertEqual(self.job_scheduler._run_threads[job.id].cancel.call_count, 1)
            self.assertFalse(self.job_scheduler._lock_cache.get_by_job(job))
        finally:
            RunJobThread.cancel = cancel_bak
            JobScheduler._spawn_job = spawn_bak
