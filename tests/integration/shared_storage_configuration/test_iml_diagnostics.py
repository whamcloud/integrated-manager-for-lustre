from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestIMLDiagnostics(ChromaIntegrationTestCase):
    TEST_SERVER = config["lustre_servers"][0]

    def test_diagnostics_with_all_logs(self):

        # Generate the diagnostics from the server
        run_result = self.remote_operations.run_iml_diagnostics(self.TEST_SERVER, verbose=True)
        self.assertEqual(run_result.rc, 0, "IML Diagnostics failed with the following error: %s" % run_result.stderr)

    def test_diagnostics_without_all_logs(self):

        # Generate the diagnostics from the server
        run_result = self.remote_operations.run_iml_diagnostics(self.TEST_SERVER, verbose=False)
        self.assertEqual(run_result.rc, 0, "IML Diagnostics failed with the following error: %s" % run_result.stderr)
