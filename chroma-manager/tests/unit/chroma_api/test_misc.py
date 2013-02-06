import dateutil.parser
from chroma_core.models.host import ManagedHost, Volume, VolumeNode
from chroma_core.models.jobs import StepResult
from chroma_core.models.target import ManagedTarget
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCaseHeavy
from tests.unit.chroma_core.helper import MockAgentRpc


class TestMisc(ChromaApiTestCaseHeavy):
    """API unit tests which are not specific to a particular resource"""
    def test_HYD648(self):
        """Test that datetimes in the API have a timezone"""
        response = self.api_client.get("/api/host/")
        self.assertHttpOK(response)
        host = self.deserialize(response)['objects'][0]
        t = dateutil.parser.parse(host['state_modified_at'])
        self.assertNotEqual(t.tzinfo, None)

    def test_removals(self):
        """Test that after objects are removed all GETs still work

        The idea is to go through a add hosts, create FS, remove FS, remove hosts
        cycle and then do a spider of the API to ensure that there aren't any
        exceptions rendering things (e.g. due to trying to dereference removed
        things incorrectly)"""

        # Create a filesystem
        response = self.api_client.post("/api/filesystem/",
            data = {
                'name': 'testfs',
                'mgt': {'volume_id': self._test_lun(self.host).id},
                'mdt': {
                    'volume_id': self._test_lun(self.host).id,
                    'conf_params': {}
                },
                'osts': [{
                    'volume_id': self._test_lun(self.host).id,
                    'conf_params': {}
                }],
                'conf_params': {}
            })
        self.assertHttpAccepted(response)
        filesystem = self.deserialize(response)['filesystem']

        host = self.deserialize(self.api_client.get("/api/host/%s/" % self.host.id))

        # Create a failed job record
        try:
            MockAgentRpc.succeed = False

            self.assertEqual(host['state'], 'lnet_up')
            host['state'] = 'lnet_down'
            response = self.api_client.put(host['resource_uri'], data = host)
            self.assertHttpAccepted(response)
            # Check we created an exception
            self.assertNotEqual(StepResult.objects.latest('id').backtrace, "")
        finally:
            MockAgentRpc.succeed = True

        # Remove everything
        response = self.api_client.delete(filesystem['resource_uri'])
        self.assertHttpAccepted(response)
        response = self.api_client.delete(filesystem['mgt']['resource_uri'])
        self.assertHttpAccepted(response)
        response = self.api_client.delete(host['resource_uri'])
        self.assertHttpAccepted(response)

        # Check everything is gone
        self.assertEqual(ManagedTarget.objects.count(), 0)
        self.assertEqual(ManagedHost.objects.count(), 0)
        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)

        # Check resources still render without exceptions
        self.spider_api()
