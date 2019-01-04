from chroma_core.models import Command
from chroma_core.models.host import ManagedHost
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
import mock
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase


class TestCommandResource(ChromaApiTestCase):
    def test_host_lists(self):
        """Test that commands which take a list of hosts as an argument
        are get the host URIs converted to host IDs (for use with HostListMixin)"""
        from chroma_api.urls import api

        hosts = []
        for i in range(0, 2):
            address = "myserver_%d" % i
            host = ManagedHost.objects.create(address=address, fqdn=address, nodename=address)
            hosts.append(host)

        with mock.patch(
            "chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.command_run_jobs",
            mock.Mock(return_value=Command.objects.create().id),
        ):
            response = self.api_client.post(
                "/api/command/",
                data={
                    "message": "Test command",
                    "jobs": [
                        {"class_name": "UpdateNidsJob", "args": {"hosts": [api.get_resource_uri(h) for h in hosts]}}
                    ],
                },
            )
            self.assertEqual(response.status_code, 201)

            host_ids = "[%s]" % ", ".join([str(h.id) for h in hosts])
            JobSchedulerClient.command_run_jobs.assert_called_once_with(
                [{"class_name": "UpdateNidsJob", "args": {"host_ids": host_ids}}], "Test command"
            )
