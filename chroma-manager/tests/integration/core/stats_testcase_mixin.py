

import logging
import time

from testconfig import config
from tests.utils import wait
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


class StatsTestCaseMixin(ChromaIntegrationTestCase):
    """
    This TestCase Mixin adds the verbose checks that stats are returning
    as expected. It is meant to be used with ChromaIntegrationTestCase using
    multiple inheritance just for the integration test classes that we
    would like to check on the stats.
    """

    # Assert we can at least request each different stat without triggering
    # an exception. This is a smoke test and many of these should have more
    # specific testing.
    mdt_stats = [
        'k',
        'stats_link',
        'stats_ldlm_ibits_enqueue',
        'stats_mkdir',
        'stats_mknod',
        'stats_mds_connect',
        'stats_mds_getattr',
        'stats_mds_getxattr',
        'stats_mds_getstatus',
        'stats_mds_statfs',
        'stats_mds_sync',
        'stats_obd_ping',
        'stats_open',
        'stats_getxattr',
        'stats_req_active',
        'stats_req_qdepth',
        'stats_req_timeout',
        'stats_req_waittime',
        'stats_reqbuf_avail',
        'stats_rename',
        'stats_rmdir',
        'stats_unlink'
    ]

    ost_stats = [
        'filesfree',
        'filestotal',
        'kbytesavail',
        'kbytesfree',
        'kbytestotal',
        'num_exports',
        'stats_commitrw',
        'stats_connect',
        'stats_create',
        'stats_destroy',
        'stats_disconnect',
        'stats_get_info',
        'stats_get_page',
        'stats_llog_init',
        'stats_ping',
        'stats_punch',
        'stats_preprw',
        'stats_set_info_async',
        'stats_statfs',
        'stats_sync',
        'stats_read_bytes',
        'stats_write_bytes',
        'tot_dirty',
        'tot_granted',
        'tot_pending'
    ]

    def assert_fs_stat(self, fs_id, name, value):
        "Wait until filesystem stat matches."
        initial = self.get_filesystem(fs_id).get(name)
        for index in wait(timeout=60):
            fs = self.get_filesystem(fs_id)
            if fs.get(name) == value:
                return fs
        self.assertEqual(fs.get(name), value, "initial {0}: {1}".format(name, initial))

    def check_stats(self, filesystem_id):
        """
        Smoke test that checks a laundry list of stats can be requested
        without exception and that a few are updated as expected when
        corresponding actions are taken. Far from exhaustive.
        """
        if config.get('simulator', False):
            # Simulator doesn't know how to map client writes to decrementing
            # OST stats
            return

        filesystem = self.get_filesystem(filesystem_id)
        client = config['lustre_clients'][0]['address']

        # Make sure client cache is flushed and stats up to date
        self.remote_operations.unmount_filesystem(client, filesystem)
        self.remote_operations.mount_filesystem(client, filesystem)
        time.sleep(20)

        # Check bytes free
        filesystem = self.get_filesystem(filesystem_id)
        bytes_total = filesystem['bytes_total']
        starting_bytes_free = filesystem['bytes_free']
        starting_files_free = filesystem['files_free']
        self.assertLessEqual(starting_bytes_free, bytes_total)

        # check value from metrics api matches
        response = self.chroma_manager.get(
            '/api/target/metric/',
            params = {
                'metrics': 'kbytesfree,kbytestotal,filesfree,filestotal',
                'latest': 'true',
                'reduce_fn': 'sum',
                'kind': 'OST',
                'group_by': 'filesystem',
            }
        )
        self.assertEqual(response.successful, True, response.text)
        metrics = [x['data'] for x in response.json.values()[0]][0]
        self.assertEqual(bytes_total / 1024, metrics['kbytestotal'])
        self.assertEqual(starting_bytes_free / 1024, metrics['kbytesfree'])
        response = self.chroma_manager.get(
            '/api/target/metric/',
            params = {
                'metrics': 'filesfree,filestotal',
                'latest': 'true',
                'reduce_fn': 'sum',
                'kind': 'MDT',
                'group_by': 'filesystem',
            }
        )
        self.assertEqual(response.successful, True, response.text)
        metrics = [x['data'] for x in response.json.values()[0]][0]
        self.assertEqual(filesystem['files_total'], metrics['filestotal'])
        self.assertEqual(starting_files_free, metrics['filesfree'])

        # Check bytes free decremented properly after writing to fs
        expected_bytes_written = min(int(starting_bytes_free * 0.9), 102400)
        self.remote_command(
            client,
            "dd if=/dev/zero of=/mnt/%s/stattest.dat bs=1000 count=%s" % (
                filesystem['name'],
                (expected_bytes_written / 1000)
            )
        )

        # Make sure client cache is flushed and check client count while we are at it
        starting_client_count = filesystem['client_count']
        self.remote_operations.unmount_filesystem(client, filesystem)
        self.remote_operations.mount_filesystem(client, filesystem)
        self.assert_fs_stat(filesystem_id, 'client_count', starting_client_count)

        # Check bytes free are what we expect after the writing above
        def _check():
            current_bytes_free = self.get_filesystem(filesystem_id).get('bytes_free')
            actual_bytes_written = starting_bytes_free - current_bytes_free
            logger.debug("expected: %s, actual: %s from starting: %s - current: %s" %
                         (expected_bytes_written, actual_bytes_written, starting_bytes_free, current_bytes_free))

            return expected_bytes_written == actual_bytes_written
        self.wait_until_true(_check)

        # Check files free are what we expect after the writing above
        self.assert_fs_stat(filesystem_id, 'files_free', starting_files_free - 1)

        #Check total bytes remained the same
        self.assertEqual(bytes_total, self.get_filesystem(filesystem_id).get('bytes_total'))

        response = self.chroma_manager.get(
            '/api/target/metric/',
            params = {
                'metrics': ','.join(self.mdt_stats),
                'latest': 'true',
                'reduce_fn': 'sum',
                'kind': 'MDT',
                'group_by': 'filesystem',
            }
        )
        self.assertEqual(response.successful, True, response.text)
        self.assertEqual(len(self.mdt_stats), len(response.json.values()[0][0].get('data')), response.json)

        response = self.chroma_manager.get(
            '/api/target/metric/',
            params = {
                'metrics': ','.join(self.ost_stats),
                'latest': 'true',
                'reduce_fn': 'sum',
                'kind': 'OST',
                'group_by': 'filesystem',
            }
        )
        self.assertEqual(response.successful, True, response.text)
        self.assertEqual(len(self.ost_stats), len(response.json.values()[0][0].get('data')), response.json)

    def get_mdt_stats(self, filesystem, index):
        response = self.chroma_manager.get(
            '/api/target/metric/',
            params = {
                'metrics': ','.join(self.mdt_stats),
                'latest': 'true',
                'reduce_fn': 'sum',
                'kind': 'MDT',
                'group_by': 'filesystem',
                'id': next(mdt['id'] for mdt in filesystem['mdts'] if mdt['index'] == index)
            }
        )

        self.assertEqual(response.successful, True, response.text)
        self.assertEqual(len(self.mdt_stats), len(response.json.values()[0][0].get('data')), response.json)

        return response.json.values()[0][0].get('data')
