
from django.test import TestCase
from mock import patch


class TestStateManager(TestCase):
    def _create_configured_host(self, address, fqdn, nids):
        from configure.models import ManagedHost
        host = ManagedHost.create_from_string('myaddress')

        # Suppress the jobs that were enqueued during host creation
        from configure.models import Job
        Job.objects.update(state = 'complete')

        # Simulate a successful SetupHostJob
        host.state = 'lnet_unloaded'
        host.fqdn = fqdn
        host.save()

        # Simulate a successful ConfigureLNetJob
        host.lnetconfiguration.state = 'nids_known'
        host.lnetconfiguration.save()
        from configure.models import Nid
        for n in nids:
            Nid.objects.get_or_create(
                    lnet_configuration = host.lnetconfiguration,
                    nid_string = n)

        # Get a fresh host instance to make sure we aren't getting
        # any stale data from the setup
        return ManagedHost.objects.get(pk = host.pk)

    def setUp(self):
        # FIXME: have to do this before every test because otherwise
        # one test will get all the setup of StoragePluginClass records,
        # the in-memory instance of storage_plugin_manager will expect
        # them to still be there but they'll have been cleaned
        # out of the database.  Setting up this stuff should be done
        # as part of the initial DB setup before any test is started
        # so that it's part of the baseline that's rolled back to
        # after each test.
        import configure.lib.storage_plugin.manager
        configure.lib.storage_plugin.manager.storage_plugin_manager = configure.lib.storage_plugin.manager.StoragePluginManager()

        # Intercept attempts to call out to hosts
        self.patch_agent = patch('configure.lib.agent.Agent')
        self.patch_agent.start()

        # Intercept attempts to created delayed tasks
        self.patch_delay_task = patch('celery.app.amqp.TaskPublisher.delay_task')
        self.patch_delay_task.start().return_value = 1

        self.host = self._create_configured_host('myaddress', 'myaddress.mycompany.com', ["192.168.0.1@tcp"])

    def tearDown(self):
        self.patch_agent.stop()
        self.patch_delay_task.stop()

    def _set_state_and_run(self, stateful_object, new_state):
        # Patch run_next to avoid attempting to .run any
        # jobs in set_state
        stateful_object = stateful_object.__class__.objects.get(pk = stateful_object.pk)
        with patch('configure.models.Job.run_next'):
            from configure.lib.state_manager import StateManager
            StateManager()._set_state(stateful_object, new_state)

            # Do a simulated run through the jobs
            from configure.models import Job
            from configure.lib.job import StateChangeJob
            from django.db.models import Q
            for j in Job.objects.filter(~Q(state = 'complete')):
                # Use .run to check dependencies
                j.run()
                self.assertEqual(j.state, 'tasked')

                # Pretend success and update the state -- only
                # works when the only side effect is the invoke_agent
                # stuff we're mocking out
                if isinstance(j, StateChangeJob):
                    new_state = j.state_transition[2]
                    obj = j.get_stateful_object()
                    obj.state = new_state
                    obj.save()

                j.state = 'complete'
                j.save()

    def test_start_target(self):
        from hydraapi.configureapi import create_target
        from configure.models import ManagedMgs
        mgt = create_target(self._test_lun(self.host).id, ManagedMgs, name = "MGS")
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unformatted')
        self._set_state_and_run(mgt, 'mounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'mounted')
        self._set_state_and_run(mgt, 'unmounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unmounted')
        self._set_state_and_run(mgt, 'mounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'mounted')
        self._set_state_and_run(mgt, 'removed')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'removed')

    def _test_lun(self, host):
        from configure.models import Lun, LunNode
        lun = Lun.objects.create(shareable = False)
        node = LunNode.objects.create(lun = lun, host = host, path = "/fake/path/%s" % lun.id, primary = True)
        return node

    def test_start_filesystem(self):
        from celery.app.amqp import TaskPublisher
        TaskPublisher.delay_task.reset_mock()

        from hydraapi.configureapi import create_fs, create_target
        from configure.models import ManagedMgs, ManagedMdt, ManagedOst
        mgt = create_target(self._test_lun(self.host).id, ManagedMgs, name = "MGS")
        fs = create_fs(mgt.pk, "testfs", {})
        mdt = create_target(self._test_lun(self.host).id, ManagedMdt, filesystem = fs)
        ost = create_target(self._test_lun(self.host).id, ManagedOst, filesystem = fs)

        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unformatted')
        self.assertEqual(ManagedMdt.objects.get(pk = mdt.pk).state, 'unformatted')
        self.assertEqual(ManagedOst.objects.get(pk = ost.pk).state, 'unformatted')

        self._set_state_and_run(fs, 'available')

        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'mounted')
        self.assertEqual(ManagedMdt.objects.get(pk = mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = ost.pk).state, 'mounted')

        self._set_state_and_run(fs, 'stopped')

        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unmounted')
        self.assertEqual(ManagedMdt.objects.get(pk = mdt.pk).state, 'unmounted')
        self.assertEqual(ManagedOst.objects.get(pk = ost.pk).state, 'unmounted')

        self._set_state_and_run(fs, 'available')

        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'mounted')
        self.assertEqual(ManagedMdt.objects.get(pk = mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = ost.pk).state, 'mounted')

        self._set_state_and_run(fs, 'removed')

        # Hey, why is this MGS getting unmounted when I remove the filesystem?
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unmounted')
        self.assertEqual(ManagedMdt.objects.get(pk = mdt.pk).state, 'removed')
        self.assertEqual(ManagedOst.objects.get(pk = ost.pk).state, 'removed')

    def test_create_host(self):
        from celery.app.amqp import TaskPublisher
        TaskPublisher.delay_task.reset_mock()

        from configure.models import ManagedHost
        host = ManagedHost.create_from_string('myaddress')

        self.assertEqual(TaskPublisher.delay_task.call_count, 2)
        calls = TaskPublisher.delay_task.call_args_list
        self.assertEqual(calls[0][0], ('configure.tasks.set_state', ((u'configure', u'managedhost'), host.id, 'lnet_unloaded'), {}))
        self.assertEqual(calls[1][0], ('configure.tasks.set_state', ((u'configure', u'lnetconfiguration'), host.lnetconfiguration.id, 'nids_known'), {}))

    def test_invalid_state(self):
        from configure.lib.state_manager import StateManager
        with self.assertRaisesRegexp(RuntimeError, "not legal state"):
            StateManager()._set_state(self.host, 'lnet_rhubarb')

    def test_load_lnet(self):
        from celery.app.amqp import TaskPublisher
        TaskPublisher.delay_task.reset_mock()

        # Should be a simple one-step operation
        from configure.lib.state_manager import StateManager
        StateManager()._set_state(self.host, 'lnet_down')

        # Should have created one Job
        from configure.models import Job
        from django.db.models import Q
        job = Job.objects.get(~Q(state = 'complete'))

        # That Job should have been started
        self.assertEqual(job.state, 'tasked')

        # That Job should have been passed to run_job
        self.assertEqual(TaskPublisher.delay_task.call_count, 1)
        calls = TaskPublisher.delay_task.call_args_list
        self.assertEqual(calls[0][0], ('configure.tasks.run_job', (job.id,), {}))
