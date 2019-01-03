from django.utils.unittest import skip
from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.core.failover_testcase_mixin import FailoverTestCaseMixin
from tests.integration.core.stats_testcase_mixin import StatsTestCaseMixin


class TestManagedFilesystemWithFailover(FailoverTestCaseMixin, StatsTestCaseMixin, ChromaIntegrationTestCase):
    TESTS_NEED_POWER_CONTROL = True

    def _test_create_filesystem_with_failover(self):
        filesystem_id = self.create_filesystem_standard(self.TEST_SERVERS)

        filesystem = self.get_filesystem(filesystem_id)

        # Define where we expect targets for volumes to be started on depending on our failover state.
        volumes_expected_hosts_in_normal_state = {
            self.standard_filesystem_layout["mgt"]["volume"]["id"]: self.standard_filesystem_layout["mgt"][
                "primary_host"
            ],
            self.standard_filesystem_layout["mdt"]["volume"]["id"]: self.standard_filesystem_layout["mdt"][
                "primary_host"
            ],
            self.standard_filesystem_layout["ost1"]["volume"]["id"]: self.standard_filesystem_layout["ost1"][
                "primary_host"
            ],
            self.standard_filesystem_layout["ost2"]["volume"]["id"]: self.standard_filesystem_layout["ost2"][
                "primary_host"
            ],
        }

        # Verify targets are started on the correct hosts
        self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_normal_state)

        # Mount the filesystem
        self.assertTrue(filesystem["mount_command"])

        client = config["lustre_clients"][0]["address"]
        self.remote_operations.mount_filesystem(client, filesystem)
        try:
            self.remote_operations.exercise_filesystem(client, filesystem)
            self.check_stats(filesystem_id)
        finally:
            self.remote_operations.unmount_filesystem(client, filesystem)

        return filesystem_id, volumes_expected_hosts_in_normal_state

    def test_create_filesystem_with_failover_mgs(self):

        filesystem_id, volumes_expected_hosts_in_normal_state = self._test_create_filesystem_with_failover()

        # Test failover if the cluster config indicates that failover has
        # been properly configured with stonith, etc.
        if config["failover_is_configured"]:
            # Test MGS failover
            volumes_expected_hosts_in_failover_state = {
                self.standard_filesystem_layout["mgt"]["volume"]["id"]: self.standard_filesystem_layout["mgt"][
                    "failover_host"
                ],
                self.standard_filesystem_layout["mdt"]["volume"]["id"]: self.standard_filesystem_layout["mdt"][
                    "primary_host"
                ],
                self.standard_filesystem_layout["ost1"]["volume"]["id"]: self.standard_filesystem_layout["ost1"][
                    "primary_host"
                ],
                self.standard_filesystem_layout["ost2"]["volume"]["id"]: self.standard_filesystem_layout["ost2"][
                    "primary_host"
                ],
            }

            self.failover(
                self.standard_filesystem_layout["mgt"]["primary_host"],
                self.standard_filesystem_layout["mgt"]["failover_host"],
                filesystem_id,
                volumes_expected_hosts_in_normal_state,
                volumes_expected_hosts_in_failover_state,
            )

            self.failback(
                self.standard_filesystem_layout["mgt"]["primary_host"],
                filesystem_id,
                volumes_expected_hosts_in_normal_state,
            )

    def test_create_filesystem_with_failover_mds(self):
        filesystem_id, volumes_expected_hosts_in_normal_state = self._test_create_filesystem_with_failover()

        # Test failover if the cluster config indicates that failover has
        # been properly configured with stonith, etc.
        if config["failover_is_configured"]:

            # Test MDS failover
            volumes_expected_hosts_in_failover_state = {
                self.standard_filesystem_layout["mgt"]["volume"]["id"]: self.standard_filesystem_layout["mgt"][
                    "primary_host"
                ],
                self.standard_filesystem_layout["mdt"]["volume"]["id"]: self.standard_filesystem_layout["mdt"][
                    "failover_host"
                ],
                self.standard_filesystem_layout["ost1"]["volume"]["id"]: self.standard_filesystem_layout["ost1"][
                    "primary_host"
                ],
                self.standard_filesystem_layout["ost2"]["volume"]["id"]: self.standard_filesystem_layout["ost2"][
                    "primary_host"
                ],
            }

            self.failover(
                self.standard_filesystem_layout["mdt"]["primary_host"],
                self.standard_filesystem_layout["mdt"]["failover_host"],
                filesystem_id,
                volumes_expected_hosts_in_normal_state,
                volumes_expected_hosts_in_failover_state,
            )

            self.failback(
                self.standard_filesystem_layout["mdt"]["primary_host"],
                filesystem_id,
                volumes_expected_hosts_in_normal_state,
            )

    @skip("Disabled until LU-9725 is fixed")
    def test_create_filesystem_with_failover_oss(self):

        filesystem_id, volumes_expected_hosts_in_normal_state = self._test_create_filesystem_with_failover()

        # Test failover if the cluster config indicates that failover has
        # been properly configured with stonith, etc.
        if config["failover_is_configured"]:

            # Test failing over an OSS
            volumes_expected_hosts_in_failover_state = {
                self.standard_filesystem_layout["mgt"]["volume"]["id"]: self.standard_filesystem_layout["mgt"][
                    "primary_host"
                ],
                self.standard_filesystem_layout["mdt"]["volume"]["id"]: self.standard_filesystem_layout["mdt"][
                    "primary_host"
                ],
                self.standard_filesystem_layout["ost1"]["volume"]["id"]: self.standard_filesystem_layout["ost1"][
                    "failover_host"
                ],
                self.standard_filesystem_layout["ost2"]["volume"]["id"]: self.standard_filesystem_layout["ost2"][
                    "primary_host"
                ],
            }

            self.failover(
                self.standard_filesystem_layout["ost1"]["primary_host"],
                self.standard_filesystem_layout["ost1"]["failover_host"],
                filesystem_id,
                volumes_expected_hosts_in_normal_state,
                volumes_expected_hosts_in_failover_state,
            )

            self.failback(
                self.standard_filesystem_layout["ost1"]["primary_host"],
                filesystem_id,
                volumes_expected_hosts_in_normal_state,
            )

    def test_create_filesystem_with_failover_oss_chroma_controlled(self):

        filesystem_id, volumes_expected_hosts_in_normal_state = self._test_create_filesystem_with_failover()

        # Test failover if the cluster config indicates that failover has
        # been properly configured with stonith, etc.
        if config["failover_is_configured"]:

            # Test failing over an OSS using chroma to do a controlled failover
            volumes_expected_hosts_in_failover_state = {
                self.standard_filesystem_layout["mgt"]["volume"]["id"]: self.standard_filesystem_layout["mgt"][
                    "primary_host"
                ],
                self.standard_filesystem_layout["mdt"]["volume"]["id"]: self.standard_filesystem_layout["mdt"][
                    "primary_host"
                ],
                self.standard_filesystem_layout["ost1"]["volume"]["id"]: self.standard_filesystem_layout["ost1"][
                    "primary_host"
                ],
                self.standard_filesystem_layout["ost2"]["volume"]["id"]: self.standard_filesystem_layout["ost2"][
                    "failover_host"
                ],
            }

            self.chroma_controlled_failover(
                self.standard_filesystem_layout["ost2"]["primary_host"],
                self.standard_filesystem_layout["ost2"]["failover_host"],
                filesystem_id,
                volumes_expected_hosts_in_normal_state,
                volumes_expected_hosts_in_failover_state,
            )

            self.failback(
                self.standard_filesystem_layout["ost2"]["primary_host"],
                filesystem_id,
                volumes_expected_hosts_in_normal_state,
            )

    def test_lnet_operational_after_failover(self):
        self.remote_operations.reset_server(self.TEST_SERVERS[0]["fqdn"])
        self.remote_operations.await_server_boot(self.TEST_SERVERS[0]["fqdn"])

        # Add two hosts
        host_addresses = [s["address"] for s in self.TEST_SERVERS[:2]]
        hosts = self.add_hosts(host_addresses)
        self.configure_power_control(host_addresses)

        self.execute_commands(["zpool import -a"], host_addresses[0], "import all pools")

        # Wait for the host to have reported the volumes and discovered HA configuration.
        ha_volumes = self.wait_for_shared_volumes(4, 2)

        self.set_volume_mounts(ha_volumes[0], hosts[0]["id"], hosts[1]["id"])
        self.set_volume_mounts(ha_volumes[1], hosts[0]["id"], hosts[1]["id"])
        self.set_volume_mounts(ha_volumes[2], hosts[1]["id"], hosts[0]["id"])
        self.set_volume_mounts(ha_volumes[3], hosts[1]["id"], hosts[0]["id"])

        # Create new filesystem such that the mgs/mdt is on the host we
        # failed over and the osts are not.
        self.create_filesystem(
            hosts,
            {
                "name": "testfs",
                "mgt": {"volume_id": ha_volumes[0]["id"]},
                "mdts": [{"volume_id": v["id"], "conf_params": {}} for v in ha_volumes[1:2]],
                "osts": [{"volume_id": v["id"], "conf_params": {}} for v in ha_volumes[2:3]],
                "conf_params": {},
            },
        )
