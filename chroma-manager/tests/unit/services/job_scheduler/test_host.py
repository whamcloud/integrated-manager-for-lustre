
import mock
from copy import deepcopy
from itertools import chain
from chroma_core.lib.cache import ObjectCache
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

from tests.unit.chroma_core.helper import MockAgentRpc, MockAgentSsh, synthetic_host, synthetic_volume_full
from chroma_core.models.host import NoLNetInfo
from tests.unit.chroma_core.helper import freshen
import django.utils.timezone
from chroma_core.models.host import ManagedHost, Volume, VolumeNode, Nid
from tests.unit.services.job_scheduler.job_test_case import JobTestCase


class TestSetup(JobTestCase):
    mock_servers = {
        'myaddress': {
            'fqdn': 'myaddress.mycompany.com',
            'nodename': 'test01.myaddress.mycompany.com',
            'nids': ["192.168.0.1@tcp"]
        }
    }

    def test_nid_learning(self):
        """Test that if a host is added and then acquired lnet_up state passively,
        we will go and get the NIDs"""
        try:
            MockAgentRpc.fail_commands = [('device_plugin', {'plugin': 'lustre'})]
            host = synthetic_host('myaddress')
        finally:
            MockAgentRpc.fail_commands = []

        self.assertState(host, 'configured')
        self.assertState(host.lnetconfiguration, 'nids_unknown')
        now = django.utils.timezone.now()
        with self.assertRaises(NoLNetInfo):
            freshen(host).lnetconfiguration.get_nids()
        JobSchedulerClient.notify(freshen(host), now, {'state': 'lnet_up'}, ['configured'])
        self.assertState(host.lnetconfiguration, 'nids_known')
        freshen(host).lnetconfiguration.get_nids()


class NidTestCase(JobTestCase):
    def setUp(self):
        super(NidTestCase, self).setUp()
        self.default_mock_servers = deepcopy(self.mock_servers)

    def tearDown(self):
        self.mock_servers = self.default_mock_servers
        super(NidTestCase, self).tearDown()

    def assertNidsCorrect(self, host):
        self.assertSetEqual(
            set([n.nid_string for n in Nid.objects.filter(lnet_configuration__host = host)]),
            set(self.mock_servers[host.address]['nids']))


class TestNidChange(NidTestCase):
    mock_servers = {
        'myaddress': {
            'fqdn': 'myaddress.mycompany.com',
            'nodename': 'test01.myaddress.mycompany.com',
            'nids': ["192.168.0.1@tcp0"]
        }
    }

    def attempt_nid_change(self, new_nids):
        host = synthetic_host('myaddress', self.mock_servers['myaddress']['nids'])
        self.set_state(host.lnetconfiguration, 'nids_known')
        self.assertNidsCorrect(host)
        self.mock_servers['myaddress']['nids'] = new_nids
        from chroma_api.urls import api
        JobSchedulerClient.command_run_jobs([{'class_name': 'RelearnNidsJob', 'args': {'hosts': [api.get_resource_uri(host)]}}], "Test relearn nids")
        self.drain_progress()
        self.assertNidsCorrect(host)

    def test_relearn_change(self):
        self.attempt_nid_change(["192.168.0.2@tcp0"])

    def test_relearn_add(self):
        self.attempt_nid_change(["192.168.0.1@tcp0", "192.168.0.2@tcp0"])

    def test_relearn_remove(self):
        self.attempt_nid_change([])


class TestUpdateNids(NidTestCase):
    mock_servers = {
        'mgs': {
            'fqdn': 'mgs.mycompany.com',
            'nodename': 'mgs.mycompany.com',
            'nids': ["192.168.0.1@tcp0"]
        },
        'mds': {
            'fqdn': 'mds.mycompany.com',
            'nodename': 'mds.mycompany.com',
            'nids': ["192.168.0.2@tcp0"]
        },
        'oss': {
            'fqdn': 'oss.mycompany.com',
            'nodename': 'oss.mycompany.com',
            'nids': ["192.168.0.3@tcp0"]
        },
    }

    def test_mgs_nid_change(self):
        mgs = synthetic_host('mgs')
        mds = synthetic_host('mds')
        oss = synthetic_host('oss')

        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem, ManagedTarget, ManagedTargetMount
        self.mgt, mgt_tms = ManagedMgs.create_for_volume(synthetic_volume_full(mgs).id, name = "MGS")
        self.fs = ManagedFilesystem.objects.create(mgs = self.mgt, name = "testfs")
        self.mdt, mdt_tms = ManagedMdt.create_for_volume(synthetic_volume_full(mds).id, filesystem = self.fs)
        self.ost, ost_tms = ManagedOst.create_for_volume(synthetic_volume_full(oss).id, filesystem = self.fs)
        ObjectCache.add(ManagedFilesystem, self.fs)
        for target in [self.mgt, self.ost, self.mdt]:
            ObjectCache.add(ManagedTarget, target.managedtarget_ptr)
        for tm in chain(mgt_tms, mdt_tms, ost_tms):
            ObjectCache.add(ManagedTargetMount, tm)

        self.set_state(self.fs, 'available')

        self.mock_servers['mgs']['nids'] = ['192.168.0.99@tcp0']
        from chroma_api.urls import api
        JobSchedulerClient.command_run_jobs([{'class_name': 'RelearnNidsJob', 'args': {'hosts': [api.get_resource_uri(mgs)]}}], "Test relearn nids")
        self.drain_progress()
        self.assertNidsCorrect(mgs)

        JobSchedulerClient.command_run_jobs([{'class_name': 'UpdateNidsJob', 'args': {'hosts': [api.get_resource_uri(mgs)]}}], "Test update nids")
        self.drain_progress()
        # The -3 looks past the start/stop that happens after writeconf
        self.assertEqual(MockAgentRpc.host_calls[mgs][-3][0], "writeconf_target")
        self.assertEqual(MockAgentRpc.host_calls[mds][-3][0], "writeconf_target")
        self.assertEqual(MockAgentRpc.host_calls[oss][-3][0], "writeconf_target")
        self.assertState(self.fs, 'stopped')


class TestHostAddRemove(JobTestCase):
    mock_servers = {
        'myaddress': {
            'fqdn': 'myaddress.mycompany.com',
            'nodename': 'test01.myaddress.mycompany.com',
            'nids': ["192.168.0.1@tcp"]
        }
    }

    def test_removal(self):
        host = synthetic_host('myaddress')
        synthetic_volume_full(host)

        self.assertEqual(Volume.objects.count(), 1)
        self.assertEqual(VolumeNode.objects.count(), 1)

        self.set_state(host, 'removed')
        with self.assertRaises(ManagedHost.DoesNotExist):
            ManagedHost.objects.get(address = 'myaddress')
        self.assertEqual(ManagedHost.objects.count(), 0)
        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)

    def test_force_removal(self):
        """Test the mode of removal which should not rely on the host
           being accessible"""
        host = synthetic_host('myaddress')

        synthetic_volume_full(host)
        self.assertEqual(Volume.objects.count(), 1)
        self.assertEqual(VolumeNode.objects.count(), 1)

        # The host disappears, never to be seen again
        MockAgentRpc.succeed = False
        try:
            JobSchedulerClient.command_run_jobs([{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host.id}}], "Test host force remove")
            self.drain_progress()
        finally:
            MockAgentRpc.succeed = True

        with self.assertRaises(ManagedHost.DoesNotExist):
            ManagedHost.objects.get(address = 'myaddress')

        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)

    def test_force_removal_with_filesystem(self):
        """Test that when a filesystem depends on a host, the filesystem
        is deleted along with the host when doing a force remove"""

        host = synthetic_host('myaddress')
        self.create_simple_filesystem(host)
        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem

        self.set_state(self.fs, 'available')
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'mounted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'mounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'available')

        # The host disappears, never to be seen again
        MockAgentRpc.succeed = False
        try:
            JobSchedulerClient.command_run_jobs([{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host.id}}], "Test host force remove")
            self.drain_progress()
        finally:
            MockAgentRpc.succeed = True

        with self.assertRaises(ManagedHost.DoesNotExist):
            ManagedHost.objects.get(address = 'myaddress')

        self.assertEqual(ManagedMgs.objects.count(), 0)
        self.assertEqual(ManagedFilesystem.objects.count(), 0)
        self.assertEqual(ManagedOst.objects.count(), 0)
        self.assertEqual(ManagedMdt.objects.count(), 0)
        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)


class TestHostAddValidations(JobTestCase):
    mock_servers = {
        'test-server': {
            'tests': {
                'auth': True,
                'resolve': True,
                'reverse_resolve': True,
                'ping': True,
                'reverse_ping': True,
                'hostname_valid': True,
                'fqdn_resolves': True,
                'fqdn_matches': True
            },
            'mgr_fqdn': "test-server.company.domain",
            'self_fqdn': "test-server.company.domain",
            'nodename': "test-server.company.domain",
            'address': "192.168.1.42"
        }
    }

    manager_http_url = "https://mock-manager.company.domain/"
    manager_address = '192.168.1.1'

    def setUp(self):
        super(TestHostAddValidations, self).setUp()
        self.maxDiff = None

        import settings
        settings.SERVER_HTTP_URL = self.manager_http_url

        def _gethostbyname(hostname):
            # Assume this is a lookup on manager of user-supplied hostname
            if (hostname in self.mock_servers
                    and self.mock_servers[hostname]['tests']['resolve']):
                return self.mock_servers[hostname]['address']

            # Lookup from server of manager address
            if (hostname in self.manager_http_url
                    and self.mock_servers['test-server']['tests']['reverse_resolve']):
                return self.manager_address

            if (hostname in self.mock_servers['test-server'].values()
                    and self.mock_servers['test-server']['tests']['fqdn_resolves']):
                if self.mock_servers['test-server']['tests']['fqdn_matches']:
                    return self.mock_servers['test-server']['address']
                else:
                    # Simulate a resolution mismatch
                    return "1.2.3.4"

            import socket
            raise socket.gaierror()

        patcher = mock.patch('socket.gethostbyname', _gethostbyname)
        patcher.start()

        def _subprocess_call(cmd):
            if "ping" in cmd:
                ping_address = cmd[-1]
                for server in self.mock_servers.values():
                    if ping_address == server['address']:
                        return 0 if server['tests']['ping'] else 1
                raise ValueError("Unable to find %s in test data" % ping_address)
            raise ValueError("Unable to mock cmd: %s" % " ".join(cmd))

        patcher = mock.patch('subprocess.call', _subprocess_call)
        patcher.start()

        # Reset to clean on each test
        for test in self.mock_servers['test-server']['tests']:
            self.mock_servers['test-server']['tests'][test] = True
        MockAgentRpc.mock_servers = self.mock_servers
        MockAgentSsh.ssh_should_fail = False

        self.expected_result = {
            u'address': u'test-server',
            u'resolve': True,
            u'ping': True,
            u'auth': True,
            u'hostname_valid': True,
            u'fqdn_resolves': True,
            u'fqdn_matches': True,
            u'reverse_resolve': True,
            u'reverse_ping': True
        }

        self.addCleanup(mock.patch.stopall)

    def _result_keys(self, excludes=[]):
        excludes.append('address')
        return [k for k in self.expected_result.keys() if k not in excludes]

    def _inject_failures(self, failed_tests, extra_failures=[]):
        failed_results = failed_tests + extra_failures
        for test in failed_tests:
            self.mock_servers['test-server']['tests'][test] = False
            if test == "auth":
                MockAgentSsh.ssh_should_fail = True

        for result in failed_results:
            self.expected_result[unicode(result)] = False

    def test_host_no_problems(self):
        self.assertEqual(self.expected_result,
                         JobSchedulerClient.test_host_contact('test-server'))

    def test_unresolvable_server_name(self):
        self._inject_failures(['resolve'], self._result_keys())
        self.assertEqual(self.expected_result,
                         JobSchedulerClient.test_host_contact('test-server'))

    def test_unpingable_server_name(self):
        # Expect everything after resolve to fail
        self._inject_failures(['ping'], self._result_keys(['resolve']))
        self.assertEqual(self.expected_result,
                         JobSchedulerClient.test_host_contact('test-server'))

    def test_auth_failure(self):
        # Expect everything after ping to fail
        self._inject_failures(['auth'], self._result_keys(['resolve', 'ping']))
        self.assertEqual(self.expected_result,
                         JobSchedulerClient.test_host_contact('test-server'))

    def test_reverse_resolve_failure(self):
        # Expect reverse_resolve and reverse_ping to fail
        self._inject_failures(['reverse_resolve'], ['reverse_ping'])
        self.assertEqual(self.expected_result,
                         JobSchedulerClient.test_host_contact('test-server'))

    def test_reverse_ping_failure(self):
        # Expect reverse_ping to fail
        self._inject_failures(['reverse_ping'])
        self.assertEqual(self.expected_result,
                         JobSchedulerClient.test_host_contact('test-server'))

    def test_bad_hostname(self):
        # Expect hostname_valid, fqdn_resolves, and fqdn_matches to fail
        self._inject_failures(['hostname_valid'],
                              ['fqdn_resolves', 'fqdn_matches'])
        self.assertEqual(self.expected_result,
                         JobSchedulerClient.test_host_contact('test-server'))

    def test_bad_fqdn(self):
        # Expect fqdn_resolves and fqdn_matches to fail
        self._inject_failures(['fqdn_resolves'], ['fqdn_matches'])
        self.assertEqual(self.expected_result,
                         JobSchedulerClient.test_host_contact('test-server'))

    def test_fqdn_mismatch(self):
        # Expect fqdn_matches to fail
        self._inject_failures(['fqdn_matches'])
        self.assertEqual(self.expected_result,
                         JobSchedulerClient.test_host_contact('test-server'))
