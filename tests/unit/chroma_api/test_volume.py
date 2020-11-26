import json

from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helpers import synthetic_host, synthetic_volume_full
from tests.unit.chroma_core.helpers import create_targets_patch
from chroma_core.models import VolumeNode


class TestVolumeNodeDelete(ChromaApiTestCase):
    """
    Make sure a deleted VolumeNode means a Volume doesn't show up as being on that Volume.
    """

    def _get_volumes(self, host_id=None):
        if host_id:
            data = {"host_id": host_id}
        else:
            data = {}

        response = self.api_client.get("/api/volume/", data=data)

        return json.loads(response.content)["objects"]

    def test_deleted_volumenode(self):
        """
        Test deleting a VolumeNode means the volume API does not return it.
        """
        host0 = synthetic_host("host0")
        host1 = synthetic_host("host1")
        synthetic_volume_full(host0, secondary_hosts=[host1])

        self.assertEqual(1, len(self._get_volumes()))
        self.assertEqual(1, len(self._get_volumes(host0.id)))
        self.assertEqual(1, len(self._get_volumes(host1.id)))

        VolumeNode.objects.get(host_id=host0.id).mark_deleted()

        self.assertEqual(0, len(self._get_volumes(host0.id)))
        self.assertEqual(1, len(self._get_volumes(host1.id)))

        VolumeNode.objects.filter(host_id=host1.id).delete()
        self.assertEqual(0, len(self._get_volumes(host1.id)))

    def test_multiple_volumenodes(self):
        """
        Test that if a Volume and multiple VolumeNodes on the same host a fetch with host_id produces a single Volume
        with multiple VolumeNodes. Previous to HYD-6331 multiple copies of the same Volume would be returned.
        """
        host0 = synthetic_host("host0")
        host1 = synthetic_host("host1")
        volume = synthetic_volume_full(host0, secondary_hosts=[host1])

        # Check we get 1 Volume with 2 VolumeNodes (check for with and without primary)
        for data in [{"host_id": host0.id}, {"host_id": host0.id, "primary": True}]:
            response = self.api_client.get("/api/volume/", data=data)

            self.assertHttpOK(response)
            content = json.loads(response.content)
            self.assertEqual(len(content["objects"]), 1)

            # Check the Volume has 2 VolumeNodes
            self.assertEqual(len(content["objects"][0]["volume_nodes"]), 2)

        # Now add another VolumeNode on host0
        VolumeNode.objects.create(volume=volume, host=host0, path="/secondvolumenode", primary=False)

        # Check we get 1 Volume again but with 3 VolumeNodes with and without primary
        for data in [{"host_id": host0.id}, {"host_id": host0.id, "primary": True}]:
            response = self.api_client.get("/api/volume/", data=data)

            self.assertHttpOK(response)
            content = json.loads(response.content)
            self.assertEqual(len(content["objects"]), 1)

            # Check the Volume has 3 VolumeNodes
            self.assertEqual(len(content["objects"][0]["volume_nodes"]), 3)

