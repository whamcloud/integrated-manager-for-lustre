from chroma_core.lib.cache import ObjectCache
from chroma_core.models import Nid
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.models import ManagedTarget, ManagedMgs, ManagedHost

from tests.unit.chroma_core.helpers import freshen
from tests.unit.chroma_core.helpers import MockAgentRpc
from tests.unit.services.job_scheduler.job_test_case import JobTestCaseWithHost


class TestMkfsOverrides(JobTestCaseWithHost):
    def test_mdt_override(self):
        import settings

        self.create_simple_filesystem(self.host, start=False)
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "mounted")

        settings.LUSTRE_MKFS_OPTIONS_MDT = "-E block_size=1024"
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mdt.managedtarget_ptr, "formatted")

        cmd, args = MockAgentRpc.skip_calls(["device_plugin", "export_target"])
        self.assertEqual(cmd, "format_target")
        self.assertDictContainsSubset({"mkfsoptions": settings.LUSTRE_MKFS_OPTIONS_MDT}, args)

    def test_ost_override(self):
        import settings

        self.create_simple_filesystem(self.host, start=False)
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "mounted")

        settings.LUSTRE_MKFS_OPTIONS_OST = "-E block_size=2048"
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.ost.managedtarget_ptr, "formatted")

        cmd, args = MockAgentRpc.skip_calls(["device_plugin", "export_target"])
        self.assertEqual(cmd, "format_target")
        self.assertDictContainsSubset({"mkfsoptions": settings.LUSTRE_MKFS_OPTIONS_OST}, args)


class TestTargetTransitions(JobTestCaseWithHost):
    def setUp(self):
        super(TestTargetTransitions, self).setUp()

        self.mgt, mgt_tms = ManagedMgs.create_for_volume(self._test_lun(self.host).id, name="MGS")
        ObjectCache.add(ManagedTarget, self.mgt.managedtarget_ptr)
        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).state, "unformatted")

    def test_start_stop(self):
        from chroma_core.models import ManagedMgs

        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "unmounted")
        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).state, "unmounted")
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "mounted")
        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).state, "mounted")

    def test_removal(self):
        from chroma_core.models import ManagedMgs

        self.mgt.managedtarget_ptr = self.set_and_assert_state(freshen(self.mgt.managedtarget_ptr), "removed")
        with self.assertRaises(ManagedMgs.DoesNotExist):
            ManagedMgs.objects.get(pk=self.mgt.pk)
        self.assertEqual(ManagedMgs._base_manager.get(pk=self.mgt.pk).state, "removed")

    def test_removal_mount_dependency(self):
        """Test that when removing, if target mounts cannot be unconfigured,
        the target is not removed"""
        from chroma_core.models import ManagedMgs

        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "mounted")
        try:
            # Make it so that the mount unconfigure operations will fail
            MockAgentRpc.succeed = False

            # -> the TargetMount removal parts of this operation will fail, we
            # want to make sure that this means that Target deletion part
            # fails as well
            self.set_and_assert_state(self.mgt.managedtarget_ptr, "removed", check=False)

            ManagedMgs.objects.get(pk=self.mgt.pk)
            self.assertNotEqual(ManagedMgs._base_manager.get(pk=self.mgt.pk).state, "removed")
        finally:
            MockAgentRpc.succeed = True

        # Now let the op go through successfully
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "removed")
        with self.assertRaises(ManagedMgs.DoesNotExist):
            ManagedMgs.objects.get(pk=self.mgt.pk)
        self.assertEqual(ManagedMgs._base_manager.get(pk=self.mgt.pk).state, "removed")

    def test_lnet_dependency(self):
        """Test that if I try to stop LNet on a host where a target is running,
        stopping the target calculated as a dependency of that"""

        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "mounted")
        self.lnet_configuration = self.assertState(self.host.lnet_configuration, "lnet_up")
        consequences = JobSchedulerClient.get_transition_consequences(self.host.lnet_configuration, "lnet_down")
        self.assertEqual(len(consequences["dependency_jobs"]), 1)
        self.assertEqual(consequences["dependency_jobs"][0]["class"], "StopTargetJob")

    def test_reformat_idempotency(self):
        """
        Test that if a volume format passes its initial check for existing filesystems,
        then it will format successfully even if the initial format operation is stopped
        and restarted.  To do that it has to pass reformat=True the second time
        """

        path = self.mgt.managedtargetmount_set.get().volume_node.path
        try:
            MockAgentRpc.fail_commands = [
                (
                    "format_target",
                    {
                        "device": path,
                        "target_types": "mgs",
                        "backfstype": "ldiskfs",
                        "device_type": "linux",
                        "target_name": "MGS",
                    },
                )
            ]

            command = self.set_and_assert_state(self.mgt.managedtarget_ptr, "formatted", check=False)
            self.assertEqual(freshen(command).complete, True)
            self.assertEqual(freshen(command).errored, True)
        finally:
            MockAgentRpc.fail_commands = []

        # Check that the initial format did not pass the reformat flag
        self.assertEqual(
            MockAgentRpc.skip_calls(["device_plugin"]),
            (
                "format_target",
                {
                    "device": path,
                    "target_types": "mgs",
                    "backfstype": "ldiskfs",
                    "device_type": "linux",
                    "target_name": "MGS",
                },
            ),
        )

        # This one should succeed
        self.set_and_assert_state(self.mgt.managedtarget_ptr, "formatted", check=True)

        # Check that it passed the reformat flag
        self.assertEqual(
            MockAgentRpc.skip_calls(["device_plugin", "export_target"]),
            (
                "format_target",
                {
                    "device": path,
                    "target_types": "mgs",
                    "backfstype": "ldiskfs",
                    "device_type": "linux",
                    "target_name": "MGS",
                    "reformat": True,
                },
            ),
        )


class TestSharedTarget(JobTestCaseWithHost):
    mock_servers = {
        "pair1": {
            "fqdn": "pair1.mycompany.com",
            "nodename": "test01.pair1.mycompany.com",
            "nids": [Nid.Nid("192.168.0.1", "tcp", 0)],
        },
        "pair2": {
            "fqdn": "pair2.mycompany.com",
            "nodename": "test02.pair2.mycompany.com",
            "nids": [Nid.Nid("192.168.0.2", "tcp", 0)],
        },
    }

    def setUp(self):
        super(TestSharedTarget, self).setUp()

        self.mgt, tms = ManagedMgs.create_for_volume(
            self._test_lun(
                ManagedHost.objects.get(address="pair1"), secondary_hosts=[ManagedHost.objects.get(address="pair2")]
            ).id,
            name="MGS",
        )

        ObjectCache.add(ManagedTarget, self.mgt.managedtarget_ptr)
        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).state, "unformatted")

    def test_clean_setup(self):
        # Start it normally the way the API would on creation
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "mounted")
        self.assertEqual(ManagedTarget.objects.get(pk=self.mgt.pk).state, "mounted")

    def test_teardown_unformatted(self):
        self.assertEqual(ManagedTarget.objects.get(pk=self.mgt.pk).state, "unformatted")
        try:
            # We should need no agent ops to remove something we never formatted
            MockAgentRpc.succeed = False
            self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "removed")
        finally:
            MockAgentRpc.succeed = True

        with self.assertRaises(ManagedTarget.DoesNotExist):
            ManagedTarget.objects.get(pk=self.mgt.pk)

    def test_teardown_friendly_user(self):
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "mounted")

        # Friendly user stops the target
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "unmounted")

        # Friendly user removes the target
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "removed")
        with self.assertRaises(ManagedTarget.DoesNotExist):
            ManagedTarget.objects.get(pk=self.mgt.pk)

        # Friendly user removes the secondary host
        self.hosts[1] = self.set_and_assert_state(self.hosts[1], "removed")

        # Friendly user removes the primary host
        self.hosts[0] = self.set_and_assert_state(self.hosts[0], "removed")
