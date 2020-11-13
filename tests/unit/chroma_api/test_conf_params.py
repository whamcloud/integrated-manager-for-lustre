import mock

from chroma_core.lib.cache import ObjectCache
from chroma_core.models import Command
from chroma_core.models.filesystem import ManagedFilesystem
from chroma_core.models.target import ManagedOst
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helpers import (
    synthetic_volume_full,
    synthetic_host,
    create_targets_patch,
    create_filesystem_patch,
)


class TestTargetPostValidation(ChromaApiTestCase):
    def setUp(self):
        super(TestTargetPostValidation, self).setUp()

        self.host = synthetic_host("myserver")
        self.create_simple_filesystem(self.host)

    @create_targets_patch
    def _new_ost_with_params(self, params):
        spare_volume = synthetic_volume_full(self.host)

        return self.api_client.post(
            "/api/target/",
            data={"kind": "OST", "filesystem_id": self.fs.id, "volume_id": spare_volume.id, "conf_params": params},
        )

    @create_targets_patch
    def test_missing(self):
        """Test that POSTs without conf_params are OK.
        This is for backwards compatability with respect to Chroma 1.0.0.0
        which didn't have conf_params on POSTs at all"""
        spare_volume = synthetic_volume_full(self.host)

        response = self.api_client.post(
            "/api/target/", data={"kind": "OST", "filesystem_id": self.fs.id, "volume_id": spare_volume.id}
        )
        self.assertHttpAccepted(response)

    def test_empty(self):
        """Test validation passes for an empty conf param dict"""
        response = self._new_ost_with_params({})

        self.assertHttpAccepted(response)

    def test_unknown_key(self):
        """Test validation of an invalid conf param key"""
        response = self._new_ost_with_params({"ost.this_is_invalid": "0"})
        self.assertHttpBadRequest(response)
        errors = self.deserialize(response)
        self.assertEqual(errors["conf_params"]["ost.this_is_invalid"], ["Unknown parameter"])

    def test_non_string(self):
        """Test validation of an invalid conf param key"""
        response = self._new_ost_with_params({"ost.max_pages_per_rpc": 0})
        self.assertHttpBadRequest(response)
        errors = self.deserialize(response)
        self.assertEqual(errors["conf_params"]["ost.max_pages_per_rpc"], ["Must be a string"])

    def test_bad_int(self):
        """Test validation of an invalid integer conf param value"""
        response = self._new_ost_with_params({"osc.max_pages_per_rpc": "custard"})
        self.assertHttpBadRequest(response)
        errors = self.deserialize(response)
        self.assertEqual(errors["conf_params"]["osc.max_pages_per_rpc"], ["Must be an integer"])

    def test_bad_enum(self):
        """Test validation of an invalid enum conf param value"""
        response = self._new_ost_with_params({"ost.sync_on_lock_cancel": "custard"})
        self.assertHttpBadRequest(response)
        errors = self.deserialize(response)
        self.assertEqual(
            errors["conf_params"]["ost.sync_on_lock_cancel"], ["Must be one of ['always', 'blocking', 'never']"]
        )

    def test_bad_boolean(self):
        """Test validation of an invalid boolean conf param value"""
        response = self._new_ost_with_params({"ost.read_cache_enable": "2"})
        self.assertHttpBadRequest(response)
        errors = self.deserialize(response)
        self.assertEqual(errors["conf_params"]["ost.read_cache_enable"], ["Must be one of ['0', '1']"])

    def test_wrong_type(self):
        """Test validation of a field which is a legitimate value for the key,
        but the key is not appropriate for this object -- setting an MDT option on an OST"""
        response = self._new_ost_with_params({"lov.qos_prio_free": "50"})
        self.assertHttpBadRequest(response)
        errors = self.deserialize(response)
        self.assertEqual(errors["conf_params"]["lov.qos_prio_free"], ["Only valid for MDT"])


class TestTargetPutValidation(ChromaApiTestCase):
    def setUp(self):
        super(TestTargetPutValidation, self).setUp()
        self.host = synthetic_host("myserver")
        self.create_simple_filesystem(self.host)

        self.filesystem = self.deserialize(self.api_client.get("/api/filesystem/"))["objects"][0]
        self.mgt = self.filesystem["mgt"]
        self.mdt = self.deserialize(self.api_client.get(self.filesystem["mdts"][0]))
        self.mdt["kind"] = "MDT"
        self.ost = self.deserialize(self.api_client.get(self.filesystem["osts"][0]))
        self.ost["kind"] = "OST"

    def test_mdt_put(self):
        """Test that conf param validation is happening on a PUT to an existing MDT"""
        self.mdt["conf_params"]["lov.qos_prio_free"] = "rhubarb"
        response = self.api_client.put(self.mdt["resource_uri"], data=self.mdt)
        self.assertHttpBadRequest(response)
        errors = self.deserialize(response)
        self.assertEqual(errors["conf_params"]["lov.qos_prio_free"], ["Must be an integer between 0 and 100"])

    def test_ost_put(self):
        self.ost["conf_params"]["osc.max_pages_per_rpc"] = "rhubarb"
        response = self.api_client.put(self.ost["resource_uri"], data=self.ost)
        self.assertHttpBadRequest(response)
        errors = self.deserialize(response)
        self.assertEqual(errors["conf_params"]["osc.max_pages_per_rpc"], ["Must be an integer"])

    def test_immutable_put(self):
        ost_record = ManagedOst.objects.get(pk=self.ost["id"])
        ost_record.immutable_state = True
        ost_record.save()
        ost = self.deserialize(self.api_client.get(self.ost["resource_uri"]))
        ost["conf_params"]["osc.max_pages_per_rpc"] = "20"
        ost["kind"] = "OST"
        response = self.api_client.put(self.ost["resource_uri"], data=ost)
        self.assertHttpBadRequest(response)
        errors = self.deserialize(response)
        self.assertEqual(errors["conf_params"], ["Cannot modify conf_params on immutable_state objects"])


class TestFilesystemConfParamValidation(ChromaApiTestCase):
    def setUp(self):
        super(TestFilesystemConfParamValidation, self).setUp()
        self.host = synthetic_host("myserver")

        # For PUTs
        self.old_command_run_jobs = JobSchedulerClient.command_run_jobs
        JobSchedulerClient.command_run_jobs = mock.Mock(side_effect=lambda jobs, msg: Command.objects.create().id)

    def tearDown(self):
        JobSchedulerClient.command_run_jobs = self.old_command_run_jobs

        ObjectCache.clear()

    @create_filesystem_patch
    def _post_filesystem(self, fs_params, mgt_params, mdt_params, ost_params):
        mgt_volume = synthetic_volume_full(self.host)
        mdt_volume = synthetic_volume_full(self.host)
        ost_volume = synthetic_volume_full(self.host)

        return self.api_client.post(
            "/api/filesystem/",
            data={
                "name": "testfs",
                "mgt": {"volume_id": mgt_volume.id, "conf_params": mgt_params},
                "mdts": [{"volume_id": mdt_volume.id, "conf_params": mdt_params}],
                "osts": [{"volume_id": ost_volume.id, "conf_params": ost_params}],
                "conf_params": fs_params,
            },
        )

    def test_post_none(self):
        """Check that a filesystem POST is accepted with empty conf param dicts"""
        response = self._post_filesystem({}, {}, {}, {})
        self.assertHttpAccepted(response)

    def test_post_valid(self):
        """Check that a filesystem POST is accepted with conf param dicts containing valid params"""
        response = self._post_filesystem(
            {"sys.at_history": "1"}, {}, {"lov.qos_prio_free": "50"}, {"osc.max_pages_per_rpc": "20"}
        )
        self.assertHttpAccepted(response)

    def test_post_invalid_mgt(self):
        """Check that a filesystem POST is rejected with bad params for mgt"""
        response = self._post_filesystem({}, {"lov.qos_prio_free": "50"}, {}, {})
        self.assertHttpBadRequest(response)
        self.assertEqual(self.deserialize(response)["mgt"]["conf_params"]["lov.qos_prio_free"], ["Only valid for MDT"])

    def test_post_invalid_ost(self):
        """Check that a filesystem POST is rejected with bad params for ost"""
        response = self._post_filesystem({}, {}, {}, {"lov.qos_prio_free": "50"})
        self.assertHttpBadRequest(response)
        self.assertEqual(self.deserialize(response)["osts"]["conf_params"]["lov.qos_prio_free"], ["Only valid for MDT"])

    def test_post_invalid_mdt(self):
        """Check that a filesystem POST is rejected with bad params for mdt"""
        response = self._post_filesystem({}, {}, {"osc.max_pages_per_rpc": "20"}, {})
        self.assertHttpBadRequest(response)
        self.assertEqual(
            self.deserialize(response)["mdts"]["conf_params"]["osc.max_pages_per_rpc"], ["Only valid for OST"]
        )

    def test_post_invalid_fs(self):
        """Check that a filesystem POST is rejected with bad params for mdt"""
        response = self._post_filesystem({"osc.max_pages_per_rpc": "20"}, {}, {}, {})
        self.assertHttpBadRequest(response)
        self.assertEqual(self.deserialize(response)["conf_params"]["osc.max_pages_per_rpc"], ["Only valid for OST"])

    def test_put_immutable_state_fs(self):
        """Check that conf param edits to an immutable_state FS are rejected"""
        self.create_simple_filesystem(self.host)
        fs_record = ManagedFilesystem.objects.get()
        fs_record.immutable_state = True
        fs_record.save()

        filesystem = self.deserialize(self.api_client.get("/api/filesystem/"))["objects"][0]
        filesystem["conf_params"]["sys.at_history"] = "1"
        response = self.api_client.put(filesystem["resource_uri"], data=filesystem)
        self.assertHttpBadRequest(response)
        self.assertEqual(
            self.deserialize(response)["conf_params"], ["Cannot modify conf_params on immutable_state objects"]
        )

    def test_put_fs_valid(self):
        """Check that valid conf params for a filesystem are accepted"""
        self.create_simple_filesystem(self.host)
        filesystem = self.deserialize(self.api_client.get("/api/filesystem/"))["objects"][0]
        filesystem["conf_params"]["sys.at_history"] = "1"
        response = self.api_client.put(filesystem["resource_uri"], data=filesystem)
        self.assertHttpAccepted(response)

    def test_put_fs_invalid(self):
        """Check that invalid conf params for a filesystem are rejected"""
        self.create_simple_filesystem(self.host)
        filesystem = self.deserialize(self.api_client.get("/api/filesystem/"))["objects"][0]
        filesystem["conf_params"]["sys.at_history"] = "rhubarb"
        response = self.api_client.put(filesystem["resource_uri"], data=filesystem)
        self.assertHttpBadRequest(response)
        self.assertEqual(self.deserialize(response)["conf_params"]["sys.at_history"], ["Must be an integer"])

    def test_put_nones(self):
        """Check that existing values can be cleared"""
        self.create_simple_filesystem(self.host)
        filesystem = self.deserialize(self.api_client.get("/api/filesystem/"))["objects"][0]
        filesystem["conf_params"]["sys.at_history"] = "10"
        response = self.api_client.put(filesystem["resource_uri"], data=filesystem)
        self.assertHttpAccepted(response)

        filesystem["conf_params"]["sys.at_history"] = None
        response = self.api_client.put(filesystem["resource_uri"], data=filesystem)
        self.assertHttpAccepted(response)

        filesystem = self.deserialize(self.api_client.get("/api/filesystem/"))["objects"][0]
        self.assertEqual(filesystem["conf_params"]["sys.at_history"], None)

    def test_put_spaces(self):
        """Check that values with trailing or leading spaces are rejected"""
        self.create_simple_filesystem(self.host)
        filesystem = self.deserialize(self.api_client.get("/api/filesystem/"))["objects"][0]
        filesystem["conf_params"]["sys.at_history"] = " 10"
        response = self.api_client.put(filesystem["resource_uri"], data=filesystem)
        self.assertHttpBadRequest(response)
        self.assertEqual(
            self.deserialize(response)["conf_params"]["sys.at_history"], ["May not contain leading or trailing spaces"]
        )
