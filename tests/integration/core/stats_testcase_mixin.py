import logging

from testconfig import config
from iml_common.lib import util
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.core import constants

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)


class StatsTestCaseMixin(ChromaIntegrationTestCase):
    """
    This TestCase Mixin adds the verbose checks that stats are returning
    as expected. It is meant to be used with ChromaIntegrationTestCase using
    multiple inheritance just for the integration test classes that we
    would like to check on the stats.
    """

    # Assert we can at least request a number of basic stats without triggering
    # an exception.
    mdt_stats = ["client_count", "filesfree", "filestotal", "kbytesfree", "kbytestotal"]

    ost_stats = [
        "filesfree",
        "filestotal",
        "kbytesavail",
        "kbytesfree",
        "kbytestotal",
        "num_exports",
        "stats_read_bytes",
        "stats_read_iops",
        "stats_write_bytes",
        "stats_write_iops",
        "tot_dirty",
        "tot_granted",
        "tot_pending",
    ]

    def _assert_fs_stat(self, fs_id, name, value):
        """ Wait until filesystem statistic matches """
        initial = self.get_filesystem(fs_id).get(name)
        for _ in util.wait(timeout=constants.TEST_TIMEOUT):
            fs = self.get_filesystem(fs_id)
            if fs.get(name) == value:
                return fs
        self.assertEqual(fs.get(name), value, "initial {0}: {1}".format(name, initial))

    def _compare_target_metric_values(self, target_kind, metric_names, fs_stat_names, filesystem_id):
        """
        Check if target metrics from manager api match expected values

        :param target_kind: kind of target e.g. MDT
        :param metric_names: list of desired metrics
        :param fs_stat_names: list of fs stat names to compare with returned target metrics
        :return: True when all values match, False otherwise
        """
        response = self.chroma_manager.get(
            "/api/target/metric/",
            params={
                "metrics": ",".join(metric_names),
                "latest": "true",
                "reduce_fn": "sum",
                "kind": target_kind,
                "group_by": "filesystem",
            },
        )
        self.assertEqual(response.successful, True, response.text)
        metrics = [metric["data"] for metric in response.json.values()[0]][0]

        self.assertTrue(len(metrics) == len(metric_names) == len(fs_stat_names))
        self.assertTrue(set(metrics.keys()) == set(metric_names))

        fs_stats = []
        for stat_name in fs_stat_names:
            value = self.get_filesystem(filesystem_id)[stat_name]
            fs_stats.append((value / 1024) if stat_name.startswith("bytes") else value)

        # logger.debug('metric names and expected values: %s/%s, actual metrics: %s' % (metric_names,
        #                                                                               fs_stats,
        #                                                                               metrics))
        return all(metrics[name] == fs_stats[metric_names.index(name)] for name in metric_names)

    def _compare_target_metric_names(self, target_kind, metric_names, filesystem_id):
        """
        Check if specific target metrics are returned from manager api, note that without the 'reduce_fn'
        url query string parameter, only metrics matching the metric_names will be returned if present
        in the MetricStore

        :param target_kind: kind of target e.g. MDT
        :param metric_names: list of desired metrics
        :return: True when all expected metrics are present in the response, False otherwise
        """
        # First verify all targets are mounted
        self.wait_until_true(lambda: self.targets_in_state("mounted"))

        response = self.chroma_manager.get(
            "/api/target/metric/", params={"metrics": ",".join(metric_names), "latest": "true", "kind": target_kind}
        )
        self.assertEqual(response.successful, True, response.text)
        targets_metrics = [x[0]["data"] for x in response.json.values()]

        fs = self.get_filesystem(filesystem_id)
        self.assertTrue(len(targets_metrics) == len(fs[target_kind.lower() + "s"]))

        logger.debug(
            "Checking target metrics are present, metrics: %s , provided metric names: %s"
            % (targets_metrics, metric_names)
        )
        return all((set(target_metrics.keys()) == set(metric_names)) for target_metrics in targets_metrics)

    def _compare_files(self, address, path1, path2, length_bytes):
        try:
            self.remote_command(address, "diff %s %s" % (path1, path2))
        except AssertionError:
            for path in [path1, path2]:
                result = self.remote_command(address, "wc -c %s" % path)
                logger.debug("file %s contains %s bytes, expected %s" % (path, result.stdout.split()[0], length_bytes))
            raise

    def _check_within_range(self, filesystem_id, stat_name, expected, _range):
        actual = self.get_filesystem(filesystem_id).get(stat_name)
        diff = actual - expected
        logger.debug("check %s diff (%s - %s = %s) is within range (%s)" % (stat_name, actual, expected, diff, _range))
        self.assertTrue(abs(diff) < _range)

    def check_stats(self, filesystem_id):
        """
        Smoke test that checks a laundry list of stats can be requested without exception and that a few are updated as
        expected when corresponding actions are taken. Far from exhaustive.
        """

        filesystem = self.get_filesystem(filesystem_id)
        filesystem_name = filesystem["name"]
        filename = "stattest.dat"
        client = config["lustre_clients"][0]["address"]

        # Make sure client cache is flushed and stats up to date
        self.remote_operations.unmount_filesystem(client, filesystem)
        self.remote_operations.mount_filesystem(client, filesystem)
        result = self.remote_command(client, "rm /mnt/%s/%s" % (filesystem_name, filename), expected_return_code=None)
        if result.exit_status == 0:
            # file was removed so we need to flush to make sure stats are up-to-date
            self.remote_operations.unmount_filesystem(client, filesystem)
            self.remote_operations.mount_filesystem(client, filesystem)

        # At start-up, validate expected list of mdt and ost stats are returned from the API before performing checks
        self.wait_until_true(
            lambda: self._compare_target_metric_names("MDT", self.mdt_stats, filesystem_id),
            "Error in verifying expected MDT metric names being returned from API",
        )
        self.wait_until_true(
            lambda: self._compare_target_metric_names("OST", self.ost_stats, filesystem_id),
            "Error in verifying expected OST metric names being returned from API",
        )

        # Wait for and keep track of client_count
        starting_client_count = 1.0
        self._assert_fs_stat(filesystem_id, "client_count", starting_client_count)

        # Check values returned by metric and filesystem API endpoints match up
        self.wait_until_true(
            lambda: self._compare_target_metric_values(
                "OST", ["kbytestotal", "kbytesfree"], ["bytes_total", "bytes_free"], filesystem_id=filesystem_id
            )
        )

        self.wait_until_true(
            lambda: self._compare_target_metric_values(
                "MDT", ["filestotal", "filesfree"], ["files_total", "files_free"], filesystem_id=filesystem_id
            )
        )

        # Record starting bytes counter values from filesystem API
        filesystem = self.get_filesystem(filesystem_id)
        bytes_total = filesystem["bytes_total"]
        starting_bytes_free = filesystem["bytes_free"]
        self.assertGreater(bytes_total, 10 * constants.MEGABYTES)
        self.assertGreater(starting_bytes_free, 10 * constants.MEGABYTES)
        self.assertLessEqual(starting_bytes_free, bytes_total)

        # Copy/write file of random data to fs
        expected_kbytes_written = min(int(starting_bytes_free * 0.9), 100 * constants.MEGABYTES) / 1024
        result = self.remote_command(
            client, "dd if=/dev/urandom of=/tmp/%s bs=1024 count=%s" % (filename, expected_kbytes_written)
        )
        self.assertTrue(
            "%s bytes " % (expected_kbytes_written * 1024) in result.stderr,
            "Unexpected number of bytes written to file",
        )

        self.remote_command(client, "cp /tmp/%s /mnt/%s/" % (filename, filesystem_name))

        # Re-mount to flush changes and verify client count
        self.remote_operations.unmount_filesystem(client, filesystem)
        self.remote_operations.mount_filesystem(client, filesystem)
        self._assert_fs_stat(filesystem_id, "client_count", starting_client_count)

        # Check bytes free decremented after writing to fs, allow 10% margin
        expected_bytes_free = starting_bytes_free - (expected_kbytes_written * 1024)
        range_in_bytes = (expected_kbytes_written * 1024) / 10
        self.wait_for_assert(
            lambda: self._check_within_range(filesystem_id, "bytes_free", expected_bytes_free, range_in_bytes)
        )

        self._compare_files(
            client, "/tmp/%s" % filename, "/mnt/%s/%s" % (filesystem_name, filename), expected_kbytes_written * 1024
        )

        # Check total bytes remain within a range of the original value
        self.wait_for_assert(
            lambda: self._check_within_range(filesystem_id, "bytes_total", bytes_total, range_in_bytes)
        )

        # Remove test file copied to mounted fs
        self.remote_command(client, "rm /mnt/%s/%s" % (filesystem_name, filename), expected_return_code=None)
