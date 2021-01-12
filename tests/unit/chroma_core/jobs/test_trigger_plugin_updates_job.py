import json

from tests.unit.chroma_core.jobs.test_jobs import TestJobs
from emf_common.lib.agent_rpc import agent_result_ok

from chroma_core.models import TriggerPluginUpdatesJob


class TestTriggerPluginUpdatesJob(TestJobs):
    def test_creation_with_plugins(self):
        self._test_creation(["steve", "bob", "jim"])

    def test_creation_without_plugins(self):
        self._test_creation([])

    def _test_creation(self, plugin_names):
        test_trigger_job = TriggerPluginUpdatesJob(
            host_ids=json.dumps(self.host_ids), plugin_names_json=json.dumps(plugin_names)
        )

        self.assertEqual(self.hosts, test_trigger_job.hosts)
        self.assertEqual(plugin_names, test_trigger_job.plugin_names)

        description_message = "Trigger plugin poll for %s plugins" % (
            "all" if plugin_names == [] else ", ".join(plugin_names)
        )

        self.assertEqual(description_message, TriggerPluginUpdatesJob.long_description(test_trigger_job))
        self.assertEqual(description_message, test_trigger_job.description())

        steps = test_trigger_job.get_steps()
        self.assertEqual(len(steps), 1)

        for host in self.hosts:
            self.add_invoke(host.fqdn, "trigger_plugin_update", {"plugin_names": plugin_names}, agent_result_ok, None)

        self.run_step(test_trigger_job, steps[0])

        self.assertRanAllInvokesInOrder()
