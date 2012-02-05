
from tests.unit.chroma_core.helper import JobTestCaseWithHost, MockAgent

from chroma_core.models import ManagedTarget, ManagedTargetMount, ManagedMgs, ManagedHost
from chroma_api.target import create_target
from chroma_core.lib.state_manager import StateManager


class TestTargetTransitions(JobTestCaseWithHost):
    def setUp(self):
        super(TestTargetTransitions, self).setUp()

        self.mgt = create_target(self._test_lun(self.host).id, ManagedMgs, name = "MGS")
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'unformatted')
        StateManager.set_state(self.mgt, 'mounted')
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'mounted')

    def test_start_stop(self):
        from chroma_core.lib.state_manager import StateManager
        from chroma_core.models import ManagedMgs
        StateManager.set_state(self.mgt, 'unmounted')
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'unmounted')
        StateManager.set_state(self.mgt, 'mounted')
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'mounted')

    def test_removal(self):
        from chroma_core.lib.state_manager import StateManager
        from chroma_core.models import ManagedMgs
        StateManager.set_state(self.mgt, 'removed')
        with self.assertRaises(ManagedMgs.DoesNotExist):
            ManagedMgs.objects.get(pk = self.mgt.pk)
        self.assertEqual(ManagedMgs._base_manager.get(pk = self.mgt.pk).state, 'removed')

    def test_removal_mount_dependency(self):
        """Test that when removing, if target mounts cannot be unconfigured,
        the target is not removed"""
        from chroma_core.lib.state_manager import StateManager
        from chroma_core.models import ManagedMgs

        try:
            # Make it so that the mount unconfigure operations will fail
            MockAgent.succeed = False

            # -> the TargetMount removal parts of this operation will fail, we
            # want to make sure that this means that Target deletion part
            # fails as well
            StateManager.set_state(self.mgt, 'removed')

            ManagedMgs.objects.get(pk = self.mgt.pk)
            self.assertNotEqual(ManagedMgs._base_manager.get(pk = self.mgt.pk).state, 'removed')
        finally:
            MockAgent.succeed = True

        # Now let the op go through successfully
        StateManager.set_state(self.mgt, 'removed')
        with self.assertRaises(ManagedMgs.DoesNotExist):
            ManagedMgs.objects.get(pk = self.mgt.pk)
        self.assertEqual(ManagedMgs._base_manager.get(pk = self.mgt.pk).state, 'removed')


class TestSharedTarget(JobTestCaseWithHost):
    mock_servers = {
            'pair1': {
                'fqdn': 'pair1.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            },
            'pair2': {
                'fqdn': 'pair2.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            }
    }

    def setUp(self):
        super(TestSharedTarget, self).setUp()

        self.target = create_target(self._test_lun(self.host).id, ManagedMgs, name = "MGS")
        self.assertEqual(ManagedMgs.objects.get(pk = self.target.pk).state, 'unformatted')

    def test_clean_setup(self):
        # Start it normally the way the API would on creation
        StateManager.set_state(self.target, 'mounted')
        self.assertEqual(ManagedTarget.objects.get(pk = self.target.pk).state, 'mounted')
        self.assertEqual(ManagedTarget.objects.get(pk = self.target.pk).active_mount, ManagedTargetMount.objects.get(host = self.hosts[0], target = self.target))

    def test_teardown_unformatted(self):
        self.assertEqual(ManagedTarget.objects.get(pk = self.target.pk).state, 'unformatted')
        try:
            # We should need no agent ops to remove something we never formatted
            MockAgent.succeed = False
            StateManager.set_state(self.target, 'removed')
        finally:
            MockAgent.succeed = True

        with self.assertRaises(ManagedTarget.DoesNotExist):
            ManagedTarget.objects.get(pk = self.target.pk)

    def test_teardown_remove_primary_host(self):
        StateManager.set_state(self.target, 'mounted')
        StateManager.set_state(self.target.primary_server(), 'removed')

        # Removing the primary server removes the target entirely
        with self.assertRaises(ManagedTargetMount.DoesNotExist):
            ManagedTargetMount.objects.get(target = self.target, primary = True)
        with self.assertRaises(ManagedTargetMount.DoesNotExist):
            ManagedTargetMount.objects.get(target = self.target, primary = False)
        with self.assertRaises(ManagedTarget.DoesNotExist):
            ManagedTarget.objects.get(pk = self.target.pk)

    def test_teardown_remove_secondary_host(self):
        StateManager.set_state(self.target, 'mounted')
        StateManager.set_state(self.target.secondary_servers()[0], 'removed')

        # Removing the secondary server removes the target entirely
        with self.assertRaises(ManagedTargetMount.DoesNotExist):
            ManagedTargetMount.objects.get(target = self.target, primary = True)
        with self.assertRaises(ManagedTargetMount.DoesNotExist):
            ManagedTargetMount.objects.get(target = self.target, primary = False)
        with self.assertRaises(ManagedTarget.DoesNotExist):
            ManagedTarget.objects.get(pk = self.target.pk)

    def test_teardown_friendly_user(self):
        StateManager.set_state(self.target, 'mounted')

        # Friendly user stops the target
        StateManager.set_state(self.target, 'unmounted')

        # NB not supporting removing individual target mounts
        # Friendly user removes secondary targetmount first
        #StateManager.set_state(self.target.managedtargetmount_set.get(primary = False), 'removed')
        #self.assertEqual(ManagedTargetMount._base_manager.get(target = self.target, primary = False).state, 'removed')
        #self.assertEqual(ManagedTargetMount._base_manager.get(target = self.target, primary = True).state, 'configured')

        # Friendly user removes the target
        StateManager.set_state(self.target, 'removed')
        with self.assertRaises(ManagedTarget.DoesNotExist):
            ManagedTarget.objects.get(pk = self.target.pk)
        with self.assertRaises(ManagedTargetMount.DoesNotExist):
            ManagedTargetMount.objects.get(target = self.target, primary = False)
        with self.assertRaises(ManagedTargetMount.DoesNotExist):
            ManagedTargetMount.objects.get(target = self.target, primary = True)

        # Friendly user removes the secondary host
        StateManager.set_state(self.hosts[1], 'removed')
        self.assertEqual(ManagedHost._base_manager.get(id=self.hosts[1].id).state, 'removed')

        # Friendly user removes the primary host
        StateManager.set_state(self.hosts[0], 'removed')
        self.assertEqual(ManagedHost._base_manager.get(id=self.hosts[0].id).state, 'removed')


# Create a target with P+S
# Add an S to an existing target
# Create a target with P, then add S
# Remove a target (remove P + S)
# Remove S (target stays)
