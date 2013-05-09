
import dateutil.parser
from chroma_core.models.host import ManagedHost, Volume, VolumeNode, ForceRemoveHostJob, StopLNetJob, HostOfflineAlert
from chroma_core.models.jobs import Command, StepResult
from chroma_core.models.target import ManagedTarget
import mock
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helper import synthetic_host


def _remove_host_resources(host_id):
    """
    In real life this would be done by ResourceManager, but in order to use that
    here we would have to have fully populated the StorageResourceRecords for all
    VolumeNodes, which is a bit heavyweight.
    """
    volume_ids = set()
    for vn in VolumeNode.objects.filter(host_id = host_id):
        vn.mark_deleted()
        volume_ids.add(vn.volume_id)

    for volume in Volume.objects.filter(pk__in = volume_ids):
        if volume.volumenode_set.count() == 0:
            volume.mark_deleted()

remove_host_resources_patch = mock.patch(
    "chroma_core.services.plugin_runner.agent_daemon_interface.AgentDaemonRpcInterface.remove_host_resources",
    new = mock.Mock(side_effect = _remove_host_resources), create = True)


class TestMisc(ChromaApiTestCase):
    """API unit tests which are not specific to a particular resource"""
    def test_HYD648(self):
        """Test that datetimes in the API have a timezone"""
        synthetic_host('myserver')
        response = self.api_client.get("/api/host/")
        self.assertHttpOK(response)
        host = self.deserialize(response)['objects'][0]
        t = dateutil.parser.parse(host['state_modified_at'])
        self.assertNotEqual(t.tzinfo, None)

    @mock.patch("chroma_core.services.http_agent.HttpAgentRpc.remove_host", new = mock.Mock(), create = True)
    @mock.patch("chroma_core.services.job_scheduler.agent_rpc.AgentRpc.remove", new = mock.Mock())
    @remove_host_resources_patch
    def test_removals(self):
        """Test that after objects are removed all GETs still work

        The idea is to go through a add hosts, create FS, remove FS, remove hosts
        cycle and then do a spider of the API to ensure that there aren't any
        exceptions rendering things (e.g. due to trying to dereference removed
        things incorrectly)"""

        host = synthetic_host('myserver')
        self.create_simple_filesystem(host)

        # Create a command/job/stepresult referencing the host
        command = Command.objects.create(message = "test command", complete = True, errored = True)
        job = StopLNetJob.objects.create(host = host, state = 'complete', errored = True)
        command.jobs.add(job)
        step_klass, args = job.get_steps()[0]
        StepResult.objects.create(job = job,
                                  backtrace = "an error", step_klass = step_klass,
                                  args = args, step_index = 0, step_count = 1,
                                  state = 'failed')

        # Create an alert/event referencing the host
        HostOfflineAlert.notify(host, True)
        self.assertEqual(len(self.deserialize(self.api_client.get("/api/alert/"))['objects']), 1)
        self.assertEqual(len(self.deserialize(self.api_client.get("/api/event/"))['objects']), 0)

        # Cause JobScheduler() to delete the objects, check the objects are gone in the API
        # and the API can still be spidered cleanly
        job = ForceRemoveHostJob(host = host)
        for step_klass, args in job.get_steps():
            step_klass(job, args, None, None, None).run(args)

        # Check everything is gone
        self.assertEqual(ManagedTarget.objects.count(), 0)
        self.assertEqual(ManagedHost.objects.count(), 0)
        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)
        self.assertListEqual(self.deserialize(self.api_client.get("/api/alert/?active=true"))['objects'], [])
        self.assertListEqual(self.deserialize(self.api_client.get("/api/volume/"))['objects'], [])
        self.assertListEqual(self.deserialize(self.api_client.get("/api/volume_node/"))['objects'], [])
        self.assertListEqual(self.deserialize(self.api_client.get("/api/target/"))['objects'], [])
        self.assertListEqual(self.deserialize(self.api_client.get("/api/host/"))['objects'], [])
        self.assertListEqual(self.deserialize(self.api_client.get("/api/filesystem/"))['objects'], [])

        # Check resources still render without exceptions
        self.spider_api()
