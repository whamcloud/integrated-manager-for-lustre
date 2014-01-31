import mock
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_api.test_misc import remove_host_resources_patch
from tests.unit.chroma_core.helper import synthetic_host

from chroma_core.models.host import ForceRemoveHostJob, RemoveHostJob, LustreClientMount, UnmountLustreFilesystemsStep


class LustreClientMountTests(ChromaApiTestCase):
    def setUp(self):
        super(LustreClientMountTests, self).setUp()

        self.host = synthetic_host(address = 'foo')
        self.create_simple_filesystem(self.host)

    @mock.patch('chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.notify')
    @mock.patch("chroma_core.services.http_agent.HttpAgentRpc.remove_host", new = mock.Mock(), create = True)
    @mock.patch("chroma_core.services.job_scheduler.agent_rpc.AgentRpc.remove", new = mock.Mock())
    @mock.patch("chroma_core.lib.job.Step.invoke_agent")
    @remove_host_resources_patch
    def test_removed_host_deletes_mount(self, notify, remove):
        mount = LustreClientMount.objects.create(host = self.host,
                                                 filesystem = self.fs,
                                                 mountpoint = '/mnt/testfs')

        # Make sure it was created and that we can see it via API
        self.assertEqual(self.api_get("/api/client_mount/%s/" % mount.id)['id'],
                         str(mount.id))

        job = RemoveHostJob(host = self.host)

        # Ensure that we unmount any filesystems before removing the host
        self.assertTrue(UnmountLustreFilesystemsStep in
                        [step[0] for step in job.get_steps()])

        # March through the job steps
        for step_klass, args in job.get_steps():
            step_klass(job, args, None, None, None).run(args)

        # The mount should have been removed when the host was removed
        with self.assertRaises(AssertionError):
            self.api_get("/api/client_mount/%s/" % mount.id)

    @mock.patch("chroma_core.services.http_agent.HttpAgentRpc.remove_host", new = mock.Mock(), create = True)
    @mock.patch("chroma_core.services.job_scheduler.agent_rpc.AgentRpc.remove", new = mock.Mock())
    @remove_host_resources_patch
    def test_force_removed_host_deletes_mount(self):
        mount = LustreClientMount.objects.create(host = self.host,
                                                 filesystem = self.fs,
                                                 mountpoint = '/mnt/testfs')

        # Make sure it was created and that we can see it via API
        self.assertEqual(self.api_get("/api/client_mount/%s/" % mount.id)['id'],
                         str(mount.id))

        job = ForceRemoveHostJob(host = self.host)

        # March through the job steps
        for step_klass, args in job.get_steps():
            step_klass(job, args, None, None, None).run(args)

        # The mount should have been removed when the host was removed
        with self.assertRaises(AssertionError):
            self.api_get("/api/client_mount/%s/" % mount.id)
