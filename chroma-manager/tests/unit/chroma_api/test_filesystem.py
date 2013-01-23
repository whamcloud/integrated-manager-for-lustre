
from chroma_core.models.target import ManagedMgs
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCaseHeavy


class TestFilesystemResource(ChromaApiTestCaseHeavy):
    def test_spider(self):
        self.spider_api()
        self.create_simple_filesystem()
        self.spider_api()

    def test_HYD1483(self):
        """Test that adding a second MGS to a host emits a useful error."""
        mgt = ManagedMgs.create_for_volume(self._test_lun(self.host).id, name = "MGS")
        mgt.save()

        new_mgt_volume = self._test_lun(self.host)
        mdt_volume = self._test_lun(self.host)
        ost_volume = self._test_lun(self.host)

        response = self.api_client.post("/api/filesystem/",
             data = {
                'name': 'testfs',
                'mgt': {'volume_id': new_mgt_volume.id},
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
        self.assertIn('only one MGS is allowed per server', errors['mgt']['volume_id'][0])

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
        self.assertDictEqual(errors, {
            'mgt': {'id': ['MGT is unmanaged']},
            'mdt': {},
            'osts': [{}],
        })

    def test_start_stop_partial(self):
        """Test operations using partial PUT containing only the state attribute, as used in Chroma 1.0.0.0 GUI"""
        self.create_simple_filesystem()
        fs_uri = "/api/filesystem/%s/" % self.fs.id
        self.api_set_state_partial(fs_uri, 'stopped')
        self.api_set_state_partial(fs_uri, 'available')
        self.api_set_state_partial(fs_uri, 'stopped')

    def test_start_stop_full(self):
        """Test operations using fully populated PUTs"""
        self.create_simple_filesystem()
        fs_uri = "/api/filesystem/%s/" % self.fs.id
        self.api_set_state_full(fs_uri, 'stopped')
        self.api_set_state_full(fs_uri, 'available')
        self.api_set_state_full(fs_uri, 'stopped')
