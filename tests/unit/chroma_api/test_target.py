import mock

from chroma_core.models import Command
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helpers.synthentic_objects import synthetic_host
from tests.unit.chroma_core.helpers.helper import (
    create_simple_fs,
    create_targets_patch,
    create_filesystem_patch,
)


class TestTargetResource(ChromaApiTestCase):
    def test_set_state_partial(self):
        """Test operations using partial PUT containing only the state attribute, as used in Chroma 1.0.0.0 GUI"""
        host = synthetic_host("myserver")
        (mgt, fs, mdt, ost) = create_simple_fs()
        self.mgt = mgt

        mgt_uri = "/api/target/%s/" % self.mgt.id
        with mock.patch("chroma_core.models.Command.set_state", mock.Mock(return_value=None)):
            self.api_set_state_partial(mgt_uri, "unmounted")
            Command.set_state.assert_called_once()

    def test_set_state_full(self):
        """Test operations using a fully populated PUT"""
        host = synthetic_host("myserver")
        (mgt, fs, mdt, ost) = create_simple_fs()
        self.mgt = mgt

        mgt_uri = "/api/target/%s/" % self.mgt.id
        with mock.patch("chroma_core.models.Command.set_state", mock.Mock(return_value=None)):
            self.api_set_state_full(mgt_uri, "unmounted")
            Command.set_state.assert_called_once()
