import mock

from chroma_core.models import Command
from chroma_core.models.target import ManagedMgs
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helpers import create_simple_fs, synthetic_host, synthetic_volume_full


class TestFilesystemResource(ChromaApiTestCase):
    def setUp(self):
        super(TestFilesystemResource, self).setUp()

        self.host = synthetic_host("myserver")

    def test_spider(self):
        self.spider_api()
        create_simple_fs()
        self.spider_api()

    def test_set_state_partial(self):
        """Test operations using partial PUT containing only the state attribute, as used in Chroma 1.0.0.0 GUI"""
        (mgt, fs, mdt, ost) = create_simple_fs()
        self.fs = fs

        fs_uri = "/api/filesystem/%s/" % self.fs.id
        with mock.patch("chroma_core.models.Command.set_state", mock.Mock(return_value=None)):
            self.api_set_state_partial(fs_uri, "stopped")
            Command.set_state.assert_called_once()

    def test_set_state_full(self):
        """Test operations using fully populated PUTs"""
        (mgt, fs, mdt, ost) = create_simple_fs()
        self.fs = fs

        fs_uri = "/api/filesystem/%s/" % self.fs.id
        with mock.patch("chroma_core.models.Command.set_state", mock.Mock(return_value=None)):
            self.api_set_state_full(fs_uri, "stopped")
            Command.set_state.assert_called_once()
