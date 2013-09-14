import mock
from django.test import TestCase
from tests.unit.chroma_core.helper import synthetic_host, load_default_profile
from chroma_core.models import HostContactAlert, HostOfflineAlert, FailoverTargetJob, FailbackTargetJob, RebootHostJob, ShutdownHostJob, PoweronHostJob, PoweroffHostJob, PowercycleHostJob


class TestAdvertisedTargetJobs(TestCase):
    def setUp(self):
        load_default_profile()

        self.target = mock.Mock()
        self.target.immutable_state = False
        self.target.failover_hosts = [synthetic_host()]
        self.target.primary_host = synthetic_host()
        self.target.active_host = self.target.primary_host

    def test_FailoverTargetJob(self):
        # Normal situation
        self.assertTrue(FailoverTargetJob.can_run(self.target))

        # Failover
        self.target.active_host = self.target.failover_hosts[0]
        self.assertFalse(FailoverTargetJob.can_run(self.target))

        # Monitor-only
        self.target.active_host = self.target.primary_host
        self.target.immutable_state = True
        self.assertFalse(FailoverTargetJob.can_run(self.target))

    def test_FailbackTargetJob(self):
        # Normal situation
        self.assertFalse(FailbackTargetJob.can_run(self.target))

        # Failback
        self.target.active_host = self.target.failover_hosts[0]
        self.assertTrue(FailbackTargetJob.can_run(self.target))

        # Monitor-only
        self.target.immutable_state = True
        self.assertFalse(FailbackTargetJob.can_run(self.target))


class TestAdvertisedHostJobs(TestCase):
    normal_host_state = 'lnet_up'

    def setUp(self):
        load_default_profile()

        self.host = synthetic_host()
        self.host.immutable_state = False
        self.host.state = self.normal_host_state

    def test_RebootHostJob(self):
        # Normal situation
        self.assertTrue(RebootHostJob.can_run(self.host))

        # Bad states
        for state in ['removed', 'undeployed', 'unconfigured']:
            self.host.state = state
            self.assertFalse(RebootHostJob.can_run(self.host))
            self.host.state = self.normal_host_state

        # Active host alerts
        for klass in [HostOfflineAlert, HostContactAlert]:
            klass.notify(self.host, True)
            self.assertFalse(RebootHostJob.can_run(self.host))
            klass.notify(self.host, False)

        # Monitor-only host
        self.host.immutable_state = True
        self.assertFalse(RebootHostJob.can_run(self.host))

    def test_ShutdownHostJob(self):
        # Normal situation
        self.assertTrue(ShutdownHostJob.can_run(self.host))

        # Bad states
        for state in ['removed', 'undeployed', 'unconfigured']:
            self.host.state = state
            self.assertFalse(ShutdownHostJob.can_run(self.host))
            self.host.state = self.normal_host_state

        # Active host alerts
        for klass in [HostOfflineAlert, HostContactAlert]:
            klass.notify(self.host, True)
            self.assertFalse(ShutdownHostJob.can_run(self.host))
            klass.notify(self.host, False)

        # Monitor-only host
        self.host.immutable_state = True
        self.assertFalse(ShutdownHostJob.can_run(self.host))


class TestAdvertisedPowerJobs(TestCase):
    def setUp(self):
        self.host = mock.Mock()
        self.host.immutable_state = False

        self.host.outlet_list = [mock.MagicMock(has_power=True),
                                 mock.MagicMock(has_power=True)]

        self.host.outlets = mock.Mock()

        def all():
            return self.host.outlet_list
        self.host.outlets.all = all

        def count():
            return len(self.host.outlet_list)
        self.host.outlets.count = count

    def test_PoweronHostJob(self):
        # Normal situation, all outlets have power
        self.assertFalse(PoweronHostJob.can_run(self.host))

        # One outlet has power
        self.host.outlet_list[0].has_power = False
        self.assertFalse(PoweronHostJob.can_run(self.host))

        # No outlets have power
        self.host.outlet_list[1].has_power = False
        self.assertTrue(PoweronHostJob.can_run(self.host))

        # Monitor-only host
        self.host.immutable_state = True
        self.assertFalse(PoweronHostJob.can_run(self.host))
        self.host.immutable_state = False

        # One outlet off, one unknown
        self.host.outlet_list[1].has_power = None
        self.assertTrue(PoweronHostJob.can_run(self.host))

        # One outlet on, one unknown
        self.host.outlet_list[0].has_power = True
        self.assertFalse(PoweronHostJob.can_run(self.host))

        # Both outlets unknown
        self.host.outlet_list[0].has_power = None
        self.assertFalse(PoweronHostJob.can_run(self.host))

        # No outlets associated
        self.host.outlet_list[:] = []
        self.assertFalse(PoweronHostJob.can_run(self.host))

    def test_PoweroffHostJob(self):
        # Monitor-only host
        self.host.immutable_state = True
        self.assertFalse(PowercycleHostJob.can_run(self.host))
        self.host.immutable_state = False

        # Normal situation, all outlets have power
        self.assertTrue(PoweroffHostJob.can_run(self.host))

        # One outlet has power
        self.host.outlet_list[0].has_power = False
        self.assertTrue(PoweroffHostJob.can_run(self.host))

        # No outlets have power
        self.host.outlet_list[1].has_power = False
        self.assertFalse(PoweroffHostJob.can_run(self.host))

        # One outlet off, one unknown
        self.host.outlet_list[1].has_power = None
        self.assertFalse(PoweroffHostJob.can_run(self.host))

        # One outlet on, one unknown
        self.host.outlet_list[0].has_power = True
        self.assertTrue(PoweroffHostJob.can_run(self.host))

        # Both outlets unknown
        self.host.outlet_list[0].has_power = None
        self.assertFalse(PoweroffHostJob.can_run(self.host))

        # No outlets associated
        self.host.outlet_list[:] = []
        self.assertFalse(PoweronHostJob.can_run(self.host))

    def test_PowercycleHostJob(self):
        # Monitor-only host
        self.host.immutable_state = True
        self.assertFalse(PowercycleHostJob.can_run(self.host))
        self.host.immutable_state = False

        # Normal situation, all outlets have power
        self.assertTrue(PowercycleHostJob.can_run(self.host))

        # One outlet has power
        self.host.outlet_list[0].has_power = False
        self.assertTrue(PowercycleHostJob.can_run(self.host))

        # No outlets have power
        self.host.outlet_list[1].has_power = False
        self.assertTrue(PowercycleHostJob.can_run(self.host))

        # One outlet off, one unknown
        self.host.outlet_list[1].has_power = None
        self.assertTrue(PowercycleHostJob.can_run(self.host))

        # One outlet on, one unknown
        self.host.outlet_list[0].has_power = True
        self.assertTrue(PowercycleHostJob.can_run(self.host))

        # Both outlets unknown
        self.host.outlet_list[0].has_power = None
        self.assertTrue(PowercycleHostJob.can_run(self.host))

        # No outlets associated
        self.host.outlet_list[:] = []
        self.assertFalse(PoweronHostJob.can_run(self.host))
