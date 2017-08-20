import os
import mock

from chroma_agent.device_plugins import lustre
from tests.command_capture_testcase import CommandCaptureTestCase
from django.utils import unittest

from chroma_agent.device_plugins.lustre import LustrePlugin


class MockLocalAudit():
    def metrics(self):
        return {'metrics': TestLustreAudit.values['metrics']}

    def properties(self):
        return {'properties': TestLustreAudit.values['properties']}


class MockActionPluginManager():
    capabilities = 0
    pass


class TestLustreAudit(unittest.TestCase):
    def mock_capabilities(self):
        return {'capabilities': TestLustreAudit.values['capabilities']}

    def mock_get_resource_locations(self):
        return {'resource locations': TestLustreAudit.values['resource_locations']}

    def mock_scan_mounts(self):
        return {'scan_mounts': TestLustreAudit.values['scan_mounts']}

    def mock_scan_packages(self):
        return {'scan_packages': TestLustreAudit.values['scan_packages']}

    def setUp(self):
        self.addCleanup(mock.patch.stopall)

        TestLustreAudit.values = {'capabilities': True,
                                 'resource_locations': True,
                                 'scan_mounts': True,
                                 'scan_packages': True,
                                 'metrics': True,
                                 'properties': True}

        mock.patch('chroma_agent.plugin_manager.ActionPluginManager',
                   MockActionPluginManager).start()

        mock.patch('chroma_agent.action_plugins.manage_targets.get_resource_locations',
                   self.mock_get_resource_locations).start()

        mock.patch('chroma_agent.device_plugins.audit.local.LocalAudit',
                   MockLocalAudit).start()

        mock.patch('chroma_agent.device_plugins.lustre.LustrePlugin._scan_mounts',
                   self.mock_scan_mounts).start()

        mock.patch('chroma_agent.device_plugins.lustre.scan_packages',
                   self.mock_scan_packages).start()

        self.lustre_plugin = LustrePlugin(None)

    def test_audit_delta_match(self):
        delta_fields = ['capabilities', 'properties', 'mounts', 'packages', 'resource_locations']

        result_all = self.lustre_plugin.update_session()
        result_none = self.lustre_plugin.update_session()

        for key in result_all:
            if key in delta_fields:
                self.assertEqual(result_none[key], None)
            else:
                # Time is a special case.
                if key == 'started_at':
                    self.assertGreater(result_none[key], result_all[key])
                else:
                    self.assertEqual(result_all[key], result_none[key])

    def test_audit_delta_no_match(self):
        result_all = self.lustre_plugin.update_session()

        for key in TestLustreAudit.values:
            TestLustreAudit.values[key] = not TestLustreAudit.values[key]

        result_match = self.lustre_plugin.update_session()

        for key in result_all:
            # Time and version and packages are a special case.
            if key == 'started_at':
                self.assertGreater(result_match[key], result_all[key])
            elif key not in ['agent_version', 'packages']:
                self.assertNotEqual(result_all[key], result_match[key])

    def test_audit_failsafe(self):
        result_all = self.lustre_plugin.update_session()

        for x in range(0, LustrePlugin.FAILSAFEDUPDATE):
            result_none = self.lustre_plugin.update_session()

        for key in result_all:
            # Time is a special case.
            if key == 'started_at':
                self.assertGreater(result_none[key], result_all[key])
            else:
                self.assertEqual(result_all[key], result_none[key])


class TestLustreScanPackages(CommandCaptureTestCase):
    '''
    This is a very incomplete test of the scan packages. But is at least some test that I added, it ensures the expected
    commands are run and does a loose check of the scanning of the repo file. Pass alphabetically sorted repo_list.
    '''
    def test_scan_packages(self):
        repo_list = sorted(['lustre-client', 'lustre', 'iml-agent', 'e2fsprogs', 'robinhood'])
        lustre.REPO_PATH = os.path.join(os.path.dirname(__file__), '../data/device_plugins/lustre/Intel-Lustre-Agent.repo')

        lustre.rpm_lib = mock.Mock()

        # supply sorted list to preserve command parameter sequence
        self.add_command(('yum', 'clean', 'all', '--disablerepo=*', '--enablerepo=' + ','.join(repo_list)))

        for repo in repo_list:
            self.add_command(('repoquery', '--disablerepo=*', '--enablerepo=%s' % repo, '-a', '--qf=%{EPOCH} %{NAME} %{VERSION} %{RELEASE} %{ARCH}'))

        scanned_packages = lustre.scan_packages()

        # sort keys before comparing with initial sorted list
        self.assertEqual(sorted(scanned_packages.keys()), repo_list)

        self.assertRanAllCommandsInOrder()
