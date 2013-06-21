
import datetime

from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.services.http_agent.host_state import HostState
from chroma_core.models import ManagedHost

import mock
from django.test import TestCase
from tests.unit.chroma_core.helper import synthetic_host, load_default_profile


class TestHealthUpdate(TestCase):
    def setUp(self):
        load_default_profile()

        self.old_notify = JobSchedulerClient.notify

        def _save(instance, time, update_attrs, from_states = []):
            """Simulate the saving of attrs on models objects by the JS"""

            print instance, time, update_attrs, from_states
            obj = instance.__class__.objects.get(pk=instance.id)
            for attr, value in update_attrs.items():
                print obj, attr, value
                obj.__setattr__(attr, value)
                obj.save()

        JobSchedulerClient.notify = mock.Mock(side_effect=_save)

    def tearDown(self):
        JobSchedulerClient.notify = self.old_notify

    def test_lnet_status_managed_server(self):
        """Test that lnet is correct base on contectivity with a managed system

        A managed server has the advantage of corosync running to control
        the lnet state when connectivity is lost.  (lustre_audit keeps
        lnet state fresh when connectivity exists.)
        """

        host = synthetic_host('test_managed')
        host.immutable_state = False  # default is managed
        host.state = 'lnet_up'
        host.save()

        self.assertEqual(host.state, 'lnet_up')

        not_used_date = datetime.datetime.utcnow()
        host_state = HostState(host.fqdn, not_used_date, not_used_date)

        host_state.update_health(True)  # server IS connected
        host = ManagedHost.objects.get(pk=host.id)
        self.assertEqual(host.state, 'lnet_up')

        #  Connectivity is lost, but since this server is managed, it should
        #  not change the state, and let  corosync do that (not in this test.)
        host_state.update_health(False)  # server IS NOT connected
        host = ManagedHost.objects.get(pk=host.id)
        self.assertEqual(host.state, "lnet_up")

    def test_lnet_status_monitor_only_server(self):

        host = synthetic_host('test_mon_only')
        host.immutable_state = True  # set monitor only
        host.state = 'lnet_up'
        host.save()

        self.assertEqual(host.state, 'lnet_up')

        not_used_date = datetime.datetime.utcnow()
        host_state = HostState(host.fqdn, not_used_date, not_used_date)

        host_state.update_health(True)  # server IS connected
        host = ManagedHost.objects.get(pk=host.id)
        self.assertEqual(host.state, 'lnet_up')

        #  Connectivity is lost, and this server is NOT managed,
        #  corosync is no installed, so mark this host lnet_down.
        host_state.update_health(False)  # server IS NOT connected
        host = ManagedHost.objects.get(pk=host.id)
        self.assertEqual(host.state, "lnet_down")
