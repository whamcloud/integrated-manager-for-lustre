import os
from mock import patch, Mock
from django.utils.unittest import skipUnless
from django.utils.unittest import skip

from testconfig import config
import logging

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)

from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestHsmCoordinatorControl(ChromaIntegrationTestCase):
    def _create_with_params(self, enabled=False):
        host_addresses = [h["address"] for h in config["lustre_servers"][:2]]
        self.hosts = self.add_hosts(host_addresses)
        self.configure_power_control(host_addresses)

        # Since the test code seems to rely on this ordering, we should
        # check for it right away and blow up if it's not as we expect.
        self.assertEqual(
            [h["address"] for h in self.hosts],
            [config["lustre_servers"][0]["address"], config["lustre_servers"][1]["address"]],
        )

        volumes = self.wait_for_shared_volumes(4, 2)

        mgt_volume = volumes[0]
        mdt_volume = volumes[1]
        ost_volume = volumes[2]
        host_ids = [h["id"] for h in self.hosts]
        self.set_volume_mounts(mgt_volume, *host_ids)
        self.set_volume_mounts(mdt_volume, *host_ids)
        self.set_volume_mounts(ost_volume, *host_ids)

        if enabled:
            mdt_params = {"mdt.hsm_control": "enabled"}
        else:
            mdt_params = {"mdt.hsm_control": "disabled"}

        self.filesystem_id = self.create_filesystem(
            self.hosts,
            {
                "name": "testfs",
                "mgt": {"volume_id": mgt_volume["id"]},
                "mdts": [{"volume_id": mdt_volume["id"], "conf_params": mdt_params}],
                "osts": [{"volume_id": ost_volume["id"], "conf_params": {}}],
                "conf_params": {"llite.max_cached_mb": "16"},
            },
        )

    def _test_params(self):
        mds = config["lustre_servers"][0]["address"]
        self.wait_until_true(
            lambda: "enabled" == self.remote_operations.read_proc(mds, "/proc/fs/lustre/mdt/testfs-MDT0000/hsm_control")
        )

    def test_hsm_coordinator_enabled_at_fs_creation(self):
        self._create_with_params(enabled=True)
        self._test_params()
        self.graceful_teardown(self.chroma_manager)


class ManagedCopytoolTestCase(ChromaIntegrationTestCase):
    def _create_copytool(self):
        test_copytool = dict(
            filesystem=self.filesystem["resource_uri"],
            host=self.worker["resource_uri"],
            bin_path="/usr/sbin/lhsmtool_posix",
            archive=1,
            mountpoint="/mnt/testfs",
            hsm_arguments="-p /tmp",
        )
        response = self.chroma_manager.post("/api/copytool/", body=test_copytool)

        self.assertTrue(response.successful, response.text)
        return response.json["copytool"]

    def setUp(self):
        self.TEST_SERVERS.append(self.config_workers[0])
        super(ManagedCopytoolTestCase, self).setUp()

        filesystem_id = self.create_filesystem_standard(self.TEST_SERVERS, hsm=True)
        self.filesystem = self.get_json_by_uri("/api/filesystem/%s" % filesystem_id)
        self.worker = self.add_hosts([self.config_workers[0]["address"]])[0]
        self.copytool = self._create_copytool()


class TestHsmCopytoolWorker(ManagedCopytoolTestCase):
    def test_worker_remove(self):
        # Start the copytool (creates a client mount, etc.)
        action = self.wait_for_action(self.copytool, state="started")
        self.set_state(self.copytool["resource_uri"], action["state"])

        # Now remove the worker with everything started and make sure
        # it all gets torn down cleanly.
        action = self.wait_for_action(self.worker, state="removed")
        command = self.set_state(self.worker["resource_uri"], action["state"], verify_successful=False)
        self.assertFalse(command["errored"] or command["cancelled"], command)


class TestHsmCopytoolManagement(ManagedCopytoolTestCase):
    def test_copytool_start_stop(self):
        action = self.wait_for_action(self.copytool, state="started")
        self.set_state(self.copytool["resource_uri"], action["state"])

        action = self.wait_for_action(self.copytool, state="stopped")
        self.set_state(self.copytool["resource_uri"], action["state"])

    def test_copytool_remove(self):
        action = self.wait_for_action(self.copytool, state="removed")
        self.set_state(self.copytool["resource_uri"], action["state"], verify_successful=False)

        self.wait_until_true(lambda: len(self.get_list("/api/copytool/")) == 0)

    def test_copytool_force_remove(self):
        action = self.wait_for_action(self.copytool, class_name="ForceRemoveCopytoolJob")
        self.run_command([action], "Test Force Remove (%s)" % self.copytool["label"])

        self.wait_until_true(lambda: len(self.get_list("/api/copytool/")) == 0)


# Use this to neuter the simulated copytool's ability to write
# events into the monitor's fifo.
def patch_fifo(obj):
    obj.fifo = Mock()


@skip("Needs implementation for real hardware")
class TestHsmCopytoolEventRelay(ManagedCopytoolTestCase):
    def _get_fifo_writer(self, copytool):
        fifo_path = os.path.join(
            self.COPYTOOL_TESTING_FIFO_ROOT, "%s-%s-events" % (copytool["host"]["address"], copytool["label"])
        )
        logger.info("Opening %s for write in test harness" % fifo_path)
        return open(fifo_path, "w", 1)

    def _get_active_operations(self):
        return self.get_list("/api/copytool_operation/", {"active": True})

    def test_restore_operation(self, *mocks):
        action = self.wait_for_action(self.copytool, state="started")
        self.set_state(self.copytool["resource_uri"], action["state"])

        # Wait until everything is really started
        self.wait_for_action(self.copytool, state="stopped")

        # Get a handle on the intake side of the pipeline
        fifo = self._get_fifo_writer(self.copytool)

        # Assert that we're starting with a clean slate (no current ops)
        self.assertEqual(len(self._get_active_operations()), 0)

        # Write a start event and see if it makes it all the way through
        fifo.write(
            '{"event_time": "2014-01-31 02:58:19 -0500", "event_type": "RESTORE_START", "total_bytes": 0, "lustre_path": "boot/vmlinuz-2.6.32-431.3.1.el6.x86_64", "source_fid": "0x200000400:0x13:0x0", "data_fid": "0x200000400:0x13:0x0"}\n'
        )

        self.wait_until_true(lambda: len(self._get_active_operations()))
        operation = self._get_active_operations()[0]

        # Report some progress, make sure that the active operation reflects
        # the update.
        fifo.write(
            '{"event_time": "2014-01-31 02:58:19 -0500", "event_type": "RESTORE_RUNNING", "current_bytes": 0, "total_bytes": 4128688, "lustre_path": "boot/vmlinuz-2.6.32-431.3.1.el6.x86_64", "source_fid": "0x200000400:0x13:0x0", "data_fid": "0x200000401:0x1:0x0"}\n'
        )

        self.wait_until_true(lambda: self._get_active_operations()[0]["updated_at"] != operation["updated_at"])

        # Finally, make sure that a finish event zeroes out the list of
        # active operations.
        fifo.write(
            '{"event_time": "2014-01-31 02:58:19 -0500", "event_type": "RESTORE_FINISH", "source_fid": "0x200000401:0x1:0x0", "data_fid": "0x200000401:0x1:0x0"}\n'
        )

        self.wait_until_true(lambda: len(self._get_active_operations()) == 0)
