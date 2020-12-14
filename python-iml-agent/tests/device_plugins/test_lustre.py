import os
import mock
from tests.lib.agent_unit_testcase import AgentUnitTestCase
from chroma_agent.device_plugins.lustre import LustrePlugin


class MockLocalAudit:
    def metrics(self):
        return {"metrics": TestLustreAudit.values["metrics"]}

    def properties(self):
        return {"properties": TestLustreAudit.values["properties"]}


class MockActionPluginManager:
    capabilities = 0
    pass


class TestLustreAudit(AgentUnitTestCase):
    def mock_capabilities(self):
        return {"capabilities": TestLustreAudit.values["capabilities"]}

    def mock_get_resource_locations(self):
        return {"resource locations": TestLustreAudit.values["resource_locations"]}

    def setUp(self):
        super(TestLustreAudit, self).setUp()

        self.addCleanup(mock.patch.stopall)

        TestLustreAudit.values = {
            "capabilities": True,
            "resource_locations": True,
            "scan_mounts": True,
            "metrics": True,
            "properties": True,
        }

        mock.patch("chroma_agent.plugin_manager.ActionPluginManager", MockActionPluginManager).start()

        mock.patch("chroma_agent.device_plugins.audit.local.LocalAudit", MockLocalAudit).start()

        self.lustre_plugin = LustrePlugin(None)

    def test_audit_delta_match(self):
        delta_fields = [
            "capabilities",
            "properties",
            "mounts",
            "packages",
            "resource_locations",
        ]

        result_all = self.lustre_plugin.update_session()
        result_none = self.lustre_plugin.update_session()

        for key in result_all:
            if key in delta_fields:
                self.assertEqual(result_none[key], None)
            else:
                # Time is a special case.
                if key == "started_at":
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
            if key == "started_at":
                self.assertGreater(result_match[key], result_all[key])
            elif key not in ["agent_version", "packages"]:
                self.assertNotEqual(result_all[key], result_match[key])

    def test_audit_failsafe(self):
        result_all = self.lustre_plugin.update_session()

        for x in range(0, LustrePlugin.FAILSAFEDUPDATE):
            result_none = self.lustre_plugin.update_session()

        for key in result_all:
            # Time is a special case.
            if key == "started_at":
                self.assertGreater(result_none[key], result_all[key])
            else:
                self.assertEqual(result_all[key], result_none[key])
