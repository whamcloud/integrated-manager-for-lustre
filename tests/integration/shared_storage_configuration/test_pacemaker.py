import logging

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase

log = logging.getLogger(__name__)


class TestPacemaker(ChromaIntegrationTestCase):
    def test_pacemaker_reverse_dependencies(self):
        filesystem_id = self.create_filesystem_standard(config["lustre_servers"][0:4])

        filesystem = self.get_json_by_uri("/api/filesystem", args={"id": filesystem_id})["objects"][0]

        mgt = self.get_json_by_uri(filesystem["mgt"]["active_host"])

        response = self.set_state_dry_run(mgt["pacemaker_configuration"], "stopped")

        self.assertEqual(len(response["dependency_jobs"]), 1)
        self.assertEqual(response["dependency_jobs"][0]["class"], "StopTargetJob")
