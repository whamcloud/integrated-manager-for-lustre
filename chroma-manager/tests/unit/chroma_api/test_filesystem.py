
from chroma_core.models.target import ManagedMgs
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase


class TestFilesystemResource(ChromaApiTestCase):
    def test_spider(self):
        self.spider_api()
        self.create_simple_filesystem()
        self.spider_api()

    def test_HYD424(self):
        """Test that filesystems can't be created using unmanaged MGSs"""
        mgt = ManagedMgs.create_for_volume(self._test_lun(self.host).id, name = "MGS")
        mgt.immutable_state = True
        mgt.save()

        # Shouldn't offer the MGS for FS creation
        response = self.api_client.get("/api/target/", data = {'kind': 'MGT', 'limit': 0, 'immutable_state': False})
        self.assertHttpOK(response)
        mgts = self.deserialize(response)['objects']
        self.assertEqual(len(mgts), 0)

        mdt_volume = self._test_lun(self.host)
        ost_volume = self._test_lun(self.host)

        # Shouldn't accept the MGS for FS creation
        response = self.api_client.post("/api/filesystem/",
             data = {
                'name': 'testfs',
                'mgt': {'id': mgt.id},
                'mdt': {
                    'volume_id': mdt_volume.id,
                    'conf_params': {}
                },
                'osts': [{
                    'volume_id': ost_volume.id,
                    'conf_params': {}
                }],
                'conf_params': {}
            })
        self.assertHttpBadRequest(response)

        errors = self.deserialize(response)
        self.assertIn('mgt', errors)
        self.assertEqual(len(errors), 1)
