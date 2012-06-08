from chroma_core.models.target import ManagedTargetMount
from tests.unit.chroma_core.helper import JobTestCaseWithHost, MockAgent, freshen

from chroma_core.models import ManagedTarget, ManagedMgs, ManagedHost


class TestMkfsOverrides(JobTestCaseWithHost):
    def test_mdt_override(self):
        import settings

        self.create_simple_filesystem(start = False)
        self.set_state(self.mgt, "mounted")

        settings.LUSTRE_MKFS_OPTIONS_MDT = "-E block_size=1024"
        self.set_state(self.mdt, "formatted")
        cmd, args = MockAgent.last_call()
        self.assertEqual(cmd, "format-target")
        self.assertDictContainsSubset({'mkfsoptions': settings.LUSTRE_MKFS_OPTIONS_MDT}, args)

    def test_ost_override(self):
        import settings

        self.create_simple_filesystem(start = False)
        self.set_state(self.mgt, "mounted")

        settings.LUSTRE_MKFS_OPTIONS_OST = "-E block_size=2048"
        self.set_state(self.ost, "formatted")
        cmd, args = MockAgent.last_call()
        self.assertEqual(cmd, "format-target")
        self.assertDictContainsSubset({'mkfsoptions': settings.LUSTRE_MKFS_OPTIONS_OST}, args)


class TestTargetTransitions(JobTestCaseWithHost):
    def setUp(self):
        super(TestTargetTransitions, self).setUp()

        self.mgt = ManagedMgs.create_for_volume(self._test_lun(self.host).id, name = "MGS")
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'unformatted')
        self.set_state(self.mgt, 'mounted')
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'mounted')

    def test_start_stop(self):
        from chroma_core.models import ManagedMgs
        self.set_state(freshen(self.mgt), 'unmounted')
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'unmounted')
        self.set_state(freshen(self.mgt), 'mounted')
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'mounted')

    def test_removal(self):
        from chroma_core.models import ManagedMgs
        self.set_state(freshen(self.mgt), 'removed')
        with self.assertRaises(ManagedMgs.DoesNotExist):
            ManagedMgs.objects.get(pk = self.mgt.pk)
        self.assertEqual(ManagedMgs._base_manager.get(pk = self.mgt.pk).state, 'removed')

    def test_removal_mount_dependency(self):
        """Test that when removing, if target mounts cannot be unconfigured,
        the target is not removed"""
        from chroma_core.models import ManagedMgs

        try:
            # Make it so that the mount unconfigure operations will fail
            MockAgent.succeed = False

            # -> the TargetMount removal parts of this operation will fail, we
            # want to make sure that this means that Target deletion part
            # fails as well
            self.set_state(self.mgt, 'removed', check = False)

            ManagedMgs.objects.get(pk = self.mgt.pk)
            self.assertNotEqual(ManagedMgs._base_manager.get(pk = self.mgt.pk).state, 'removed')
        finally:
            MockAgent.succeed = True

        # Now let the op go through successfully
        self.set_state(self.mgt, 'removed')
        with self.assertRaises(ManagedMgs.DoesNotExist):
            ManagedMgs.objects.get(pk = self.mgt.pk)
        self.assertEqual(ManagedMgs._base_manager.get(pk = self.mgt.pk).state, 'removed')


class TestSharedTarget(JobTestCaseWithHost):
    mock_servers = {
            'pair1': {
                'fqdn': 'pair1.mycompany.com',
                'nodename': 'test01.pair1.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            },
            'pair2': {
                'fqdn': 'pair2.mycompany.com',
                'nodename': 'test02.pair2.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            }
    }

    def setUp(self):
        super(TestSharedTarget, self).setUp()

        self.target = ManagedMgs.create_for_volume(
            self._test_lun(
                ManagedHost.objects.get(address='pair1'),
                ManagedHost.objects.get(address='pair2')
            ).id,
            name = "MGS")
        self.assertEqual(ManagedMgs.objects.get(pk = self.target.pk).state, 'unformatted')

    def test_clean_setup(self):
        # Start it normally the way the API would on creation
        self.set_state(self.target, 'mounted')
        self.assertEqual(ManagedTarget.objects.get(pk = self.target.pk).state, 'mounted')
        self.assertEqual(ManagedTarget.objects.get(pk = self.target.pk).active_mount, ManagedTargetMount.objects.get(host = self.hosts[0], target = self.target))

    def test_teardown_unformatted(self):
        self.assertEqual(ManagedTarget.objects.get(pk = self.target.pk).state, 'unformatted')
        try:
            # We should need no agent ops to remove something we never formatted
            MockAgent.succeed = False
            self.set_state(self.target, 'removed')
        finally:
            MockAgent.succeed = True

        with self.assertRaises(ManagedTarget.DoesNotExist):
            ManagedTarget.objects.get(pk = self.target.pk)

    def test_teardown_remove_primary_host(self):
        self.set_state(self.target, 'mounted')
        self.set_state(self.target.primary_server(), 'removed')

        # Removing the primary server removes the target
        with self.assertRaises(ManagedTarget.DoesNotExist):
            ManagedTarget.objects.get(pk = self.target.pk)

    def test_teardown_remove_secondary_host(self):
        self.set_state(self.target, 'mounted')
        self.set_state(self.target.secondary_servers()[0], 'removed')

        # Removing the secondary server removes the target
        with self.assertRaises(ManagedTarget.DoesNotExist):
            ManagedTarget.objects.get(pk = self.target.pk)

    def test_teardown_friendly_user(self):
        self.set_state(self.target, 'mounted')

        # Friendly user stops the target
        self.set_state(self.target, 'unmounted')

        # Friendly user removes the target
        self.set_state(self.target, 'removed')
        with self.assertRaises(ManagedTarget.DoesNotExist):
            ManagedTarget.objects.get(pk = self.target.pk)

        # Friendly user removes the secondary host
        self.set_state(self.hosts[1], 'removed')
        self.assertEqual(ManagedHost._base_manager.get(id=self.hosts[1].id).state, 'removed')

        # Friendly user removes the primary host
        self.set_state(self.hosts[0], 'removed')
        self.assertEqual(ManagedHost._base_manager.get(id=self.hosts[0].id).state, 'removed')
