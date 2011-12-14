
from django.test import TestCase


class MockAgent(object):
    label_counter = 0
    mock_servers = {}

    succeed = True

    def __init__(self, host, log = None, console_callback = None, timeout = None):
        self.host = host

    def invoke(self, cmdline):
        if not self.succeed:
            raise RuntimeError("Test-generated failure")

        print "invoke_agent %s %s" % (self.host, cmdline)
        if cmdline == "get-fqdn":
            return self.mock_servers[self.host.address]['fqdn']
        elif cmdline == "lnet-scan":
            return self.mock_servers[self.host.address]['nids']
        elif cmdline.startswith("format-target"):
            import uuid
            return {'uuid': uuid.uuid1().__str__()}
        elif cmdline.startswith('start-target'):
            # FIXME: this will be nodename when HYD-455 is done
            return {'location': self.host.fqdn}
        elif cmdline.startswith('register-target'):
            self.label_counter += 1
            return {'label': "foofs-TTT%04d" % self.label_counter}


class JobTestCase(TestCase):
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

        # NB by this stage celery has already read in its settings, so we have to update
        # ALWAYS_EAGER inside celery instead of in settings.*
        from celery.app import app_or_default
        self.old_celery_always_eager = app_or_default().conf.CELERY_ALWAYS_EAGER
        app_or_default().conf.CELERY_ALWAYS_EAGER = True
        self.old_celery_eager_propagates_exceptions = app_or_default().conf.CELERY_EAGER_PROPAGATES_EXCEPTIONS
        app_or_default().conf.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        # Intercept attempts to call out to lustre servers
        import configure.lib.agent
        self.old_agent = configure.lib.agent.Agent
        MockAgent.mock_servers = self.mock_servers
        configure.lib.agent.Agent = MockAgent

        from configure.models import ManagedHost
        self.host = ManagedHost.create_from_string('myaddress')
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).lnetconfiguration.state, 'nids_known')

    def tearDown(self):
        import configure.lib.agent
        configure.lib.agent.Agent = self.old_agent

        from celery.app import app_or_default
        app_or_default().conf.CELERY_ALWAYS_EAGER = self.old_celery_always_eager
        app_or_default().conf.CELERY_ALWAYS_EAGER = self.old_celery_eager_propagates_exceptions


class TestStateManager(JobTestCase):
    mock_servers = {
            'myaddress': {
                'fqdn': 'myaddress.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            }
    }

    def test_start_target(self):
        from hydraapi.configureapi import create_target
        from configure.models import ManagedMgs
        from configure.lib.state_manager import StateManager
        mgt = create_target(self._test_lun(self.host).id, ManagedMgs, name = "MGS")
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unformatted')
        StateManager.set_state(mgt, 'mounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'mounted')
        StateManager.set_state(mgt, 'unmounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unmounted')
        StateManager.set_state(mgt, 'mounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'mounted')
        StateManager.set_state(mgt, 'removed')
        with self.assertRaises(ManagedMgs.DoesNotExist):
            ManagedMgs.objects.get(pk = mgt.pk)
        self.assertEqual(ManagedMgs._base_manager.get(pk = mgt.pk).state, 'removed')

    def _test_lun(self, host):
        from configure.models import Lun, LunNode
        lun = Lun.objects.create(shareable = False)
        node = LunNode.objects.create(lun = lun, host = host, path = "/fake/path/%s" % lun.id, primary = True)
        return node

    def test_start_filesystem(self):
        from hydraapi.configureapi import create_fs, create_target
        from configure.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem
        mgt = create_target(self._test_lun(self.host).id, ManagedMgs, name = "MGS")
        fs = create_fs(mgt.pk, "testfs", {})
        mdt = create_target(self._test_lun(self.host).id, ManagedMdt, filesystem = fs)
        ost = create_target(self._test_lun(self.host).id, ManagedOst, filesystem = fs)

        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unformatted')
        self.assertEqual(ManagedMdt.objects.get(pk = mdt.pk).state, 'unformatted')
        self.assertEqual(ManagedOst.objects.get(pk = ost.pk).state, 'unformatted')

        from configure.lib.state_manager import StateManager
        StateManager.set_state(fs, 'available')

        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'mounted')
        self.assertEqual(ManagedMdt.objects.get(pk = mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = ost.pk).state, 'mounted')

        StateManager.set_state(fs, 'stopped')

        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unmounted')
        self.assertEqual(ManagedMdt.objects.get(pk = mdt.pk).state, 'unmounted')
        self.assertEqual(ManagedOst.objects.get(pk = ost.pk).state, 'unmounted')

        StateManager.set_state(fs, 'available')

        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'mounted')
        self.assertEqual(ManagedMdt.objects.get(pk = mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = ost.pk).state, 'mounted')

        StateManager.set_state(ManagedMdt.objects.get(pk = mdt.pk), 'unmounted')
        self.assertEqual(ManagedMdt.objects.get(pk = mdt.pk).state, 'unmounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = fs.pk).state, 'unavailable')

        StateManager.set_state(fs, 'removed')

        # FIXME: Hey, why is this MGS getting unmounted when I remove the filesystem?
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unmounted')

        with self.assertRaises(ManagedMdt.DoesNotExist):
            ManagedMdt.objects.get(pk = mdt.pk)
        self.assertEqual(ManagedMdt._base_manager.get(pk = mdt.pk).state, 'removed')
        with self.assertRaises(ManagedOst.DoesNotExist):
            ManagedOst.objects.get(pk = ost.pk)
        self.assertEqual(ManagedOst._base_manager.get(pk = ost.pk).state, 'removed')

    def test_opportunistic_execution(self):
        # Set up an MGS, leave it offline
        from hydraapi.configureapi import create_fs, create_target
        from configure.models import ManagedMgs, ManagedMdt, ManagedOst
        mgt = create_target(self._test_lun(self.host).id, ManagedMgs, name = "MGS")
        fs = create_fs(mgt.pk, "testfs", {})
        create_target(self._test_lun(self.host).id, ManagedMdt, filesystem = fs)
        create_target(self._test_lun(self.host).id, ManagedOst, filesystem = fs)

        from configure.lib.state_manager import StateManager
        StateManager.set_state(ManagedMgs.objects.get(pk = mgt.pk), 'unmounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unmounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version, 0)
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version_applied, 0)

        try:
            # Make it so that an MGS start operation will fail
            MockAgent.succeed = False

            from hydraapi.configureapi import set_target_conf_param
            params = {"llite.max_cached_mb": "32"}
            set_target_conf_param(fs.pk, params, True)

            self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version, 1)
            self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version_applied, 0)
        finally:
            MockAgent.succeed = True

        StateManager.set_state(mgt, 'mounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'mounted')

        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version, 1)
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version_applied, 1)

    def test_invalid_state(self):
        from configure.lib.state_manager import StateManager
        with self.assertRaisesRegexp(RuntimeError, "is invalid for"):
            StateManager.set_state(self.host, 'lnet_rhubarb')

    def test_1step(self):
        # Should be a simple one-step operation
        from configure.lib.state_manager import StateManager
        from configure.models import ManagedHost
        # Our self.host is initially lnet_up
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        # This tests a state transition which is done by a single job
        StateManager.set_state(self.host, 'lnet_down')
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_down')

    def test_2steps(self):
        from configure.lib.state_manager import StateManager
        from configure.models import ManagedHost
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        # This tests a state transition which requires two jobs acting on the same object
        StateManager.set_state(self.host, 'lnet_unloaded')
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_unloaded')
