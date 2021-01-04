from chroma_core.models import Nid
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.models import ManagedTarget, ManagedMgs

from tests.unit.chroma_core.helpers.helper import create_simple_fs
from tests.unit.services.job_scheduler.job_test_case import JobTestCaseWithHost


class TestTargetTransitions(JobTestCaseWithHost):
    def setUp(self):
        super(TestTargetTransitions, self).setUp()

        (mgt, fs, mdt, ost) = create_simple_fs()
        self.mgt = mgt
        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).state, "unmounted")

    def test_start_stop(self):
        from chroma_core.models import ManagedMgs

        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "unmounted")
        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).state, "unmounted")
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "mounted")
        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).state, "mounted")

    def test_lnet_dependency(self):
        """Test that if I try to stop LNet on a host where a target is running,
        stopping the target calculated as a dependency of that"""

        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "mounted")
        self.lnet_configuration = self.assertState(self.host.lnet_configuration, "lnet_up")
        consequences = JobSchedulerClient.get_transition_consequences(self.host.lnet_configuration, "lnet_down")
        self.assertEqual(len(consequences["dependency_jobs"]), 1)
        self.assertEqual(consequences["dependency_jobs"][0]["class"], "StopTargetJob")


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

        (mgt, fs, mdt, ost) = create_simple_fs()
        self.mgt = mgt

        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).state, "unmounted")

    def test_clean_setup(self):
        # Start it normally the way the API would on creation
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "mounted")
        self.assertEqual(ManagedTarget.objects.get(pk=self.mgt.pk).state, "mounted")
