from django.utils import unittest
from mock import patch

from chroma_agent.device_plugins.lustre import LustrePlugin


class MockLocalAudit():
    def metrics(self):
        return {'metrics': TestLustreScan.values['metrics']}

    def properties(self):
        return {'properties': TestLustreScan.values['properties']}


class MockActionPluginManager():
    capabilities = 0
    pass


class TestLustreScan(unittest.TestCase):
    def mock_capabilities(self):
        return {'capabilities': TestLustreScan.values['capabilities']}

    def mock_get_resource_locations(self):
        return {'resource locations': TestLustreScan.values['resource_locations']}

    def mock_scan_mounts(self):
        return {'scan_mounts': TestLustreScan.values['scan_mounts']}

    def mock_scan_packages(self):
        return {'scan_packages': TestLustreScan.values['scan_packages']}

    def setUp(self):
        self.addCleanup(patch.stopall)

        TestLustreScan.values = {'capabilities': True,
                                 'resource_locations': True,
                                 'scan_mounts': True,
                                 'scan_packages': True,
                                 'metrics': True,
                                 'properties': True}

        patch('chroma_agent.plugin_manager.ActionPluginManager',
              MockActionPluginManager).start()

        patch('chroma_agent.action_plugins.manage_targets.get_resource_locations',
              self.mock_get_resource_locations).start()

        patch('chroma_agent.device_plugins.audit.local.LocalAudit',
              MockLocalAudit).start()

        patch('chroma_agent.device_plugins.lustre.LustrePlugin._scan_mounts',
              self.mock_scan_mounts).start()

        patch('chroma_agent.device_plugins.lustre.scan_packages',
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

        for key in TestLustreScan.values:
            TestLustreScan.values[key] = not TestLustreScan.values[key]

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
