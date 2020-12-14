import os
import tempfile
import shutil
from mock import patch, Mock

import unittest

from chroma_agent.copytool_monitor import Copytool, CopytoolEventRelay, CopytoolMonitor


class CopytoolTestCase(unittest.TestCase):
    def setUp(self):
        super(CopytoolTestCase, self).setUp()

        from chroma_agent.config_store import ConfigStore

        self.mock_config = ConfigStore(tempfile.mkdtemp())
        patch("chroma_agent.copytool_monitor.config", self.mock_config).start()

        self.ct_id = "42"
        self.ct_bin_path = "/usr/sbin/lhsmtool_foo"
        self.ct_filesystem = "testfs"
        self.ct_mountpoint = "/mnt/testfs"
        self.ct_archive = 2
        self.ct_index = 0
        self.ct = Copytool(
            self.ct_id,
            self.ct_index,
            self.ct_bin_path,
            self.ct_archive,
            self.ct_filesystem,
            self.ct_mountpoint,
            "",
        )

        self.addCleanup(patch.stopall)

    def tearDown(self):
        super(CopytoolTestCase, self).tearDown()

        shutil.rmtree(self.mock_config.path)

    def test_copytool_event_fifo(self):
        self.mock_config.set("settings", "agent", {"copytool_fifo_directory": "/var/spool"})
        self.assertEqual(self.ct.event_fifo, "/var/spool/%s-events" % self.ct)

    def test_copytool_as_dict(self):
        self.assertDictEqual(
            self.ct.as_dict(),
            dict(
                id=self.ct.id,
                index=self.ct.index,
                bin_path=self.ct.bin_path,
                archive_number=self.ct.archive_number,
                filesystem=self.ct.filesystem,
                mountpoint=self.ct.mountpoint,
                hsm_arguments=self.ct.hsm_arguments,
            ),
        )


def raise_exception(e):
    raise e


class CopytoolMonitorTestCase(unittest.TestCase):
    def setUp(self):
        super(CopytoolMonitorTestCase, self).setUp()

        self.client = Mock()

        self.copytool = Mock()
        self.copytool.event_fifo = "/var/spool/test-fifo"

        self.monitor = CopytoolMonitor(self.client, self.copytool)

        self.addCleanup(patch.stopall)

    @patch("chroma_agent.copytool_monitor.lsof")
    @patch("os.mkfifo")
    @patch("os.open")
    def test_open_fifo_normal(self, m_open, m_mkfifo, m_lsof):
        self.monitor.open_fifo()

        m_mkfifo.assert_called_with(self.copytool.event_fifo)
        m_lsof.assert_called_with(file=self.copytool.event_fifo)
        m_open.assert_called_with(self.copytool.event_fifo, os.O_RDONLY | os.O_NONBLOCK)

    @patch("chroma_agent.copytool_monitor.lsof")
    @patch("os.mkfifo", side_effect=lambda x: raise_exception(OSError(17, "foo")))
    @patch("os.open")
    def test_open_fifo_exists(self, m_open, m_mkfifo, m_lsof):
        self.monitor.open_fifo()

        m_mkfifo.assert_called_with(self.copytool.event_fifo)

    @patch("os.mkfifo")
    @patch("os.open")
    def test_open_fifo_reader_conflict(self, *mocks):
        def fake_lsof(**kwargs):
            return {"1234": {self.copytool.event_fifo: {"mode": "r"}}}

        with patch("chroma_agent.copytool_monitor.lsof", fake_lsof):
            from chroma_agent.copytool_monitor import FifoReaderConflict

            with self.assertRaises(FifoReaderConflict):
                self.monitor.open_fifo()


class CopytoolEventRelayTestCase(unittest.TestCase):
    def setUp(self):
        super(CopytoolEventRelayTestCase, self).setUp()

        self.client = Mock()
        self.client.fqdn = "fake-client"

        self.copytool = Mock()
        self.copytool.id = "42"
        self.copytool.index = 0
        self.copytool.bin_path = "/usr/sbin/lhsmtool_foo"
        self.copytool.filesystem = "testfs"
        self.copytool.archive_number = 1

        self.relay = CopytoolEventRelay(self.copytool, self.client)

        self.test_event = '{"event_time": "2013-09-27 17:26:32 -0400", "event_type": "REGISTER", "archive": 1, "mount_point": "/mnt/testfs", "uuid": "ea370e22-b5ac-ab98-71bb-605d217071f7"}'

    def test_event_relay(self):
        # The important things to test here are:
        # 1. That the incoming JSON event is added to an envelope suitable
        #    for relay to the manager.
        # 2. That the event time is converted to UTC.
        expected_envelope = dict(
            events=[
                dict(
                    uuid="ea370e22-b5ac-ab98-71bb-605d217071f7",
                    mount_point="/mnt/testfs",
                    event_type="REGISTER",
                    event_time="2013-09-27 21:26:32+00:00",
                    archive=1,
                )
            ],
            fqdn=self.client.fqdn,
            copytool=self.copytool.id,
        )

        self.relay.put(self.test_event)
        self.relay.send()
        self.client.post.assert_called_with(expected_envelope)

    def test_relay_retry(self):
        # Basic test to verify that we handle POST errors with a retry
        # after a backoff.
        from chroma_agent.copytool_monitor import RELAY_POLL_INTERVAL
        from chroma_agent.agent_client import HttpError, MIN_SESSION_BACKOFF

        def raise_error(self):
            raise HttpError("blam")

        # Establish that we're polling as usual to begin with.
        self.assertEqual(self.relay.poll_interval, RELAY_POLL_INTERVAL)

        # Inject a failure to POST.
        with patch.object(self.client, "post", side_effect=raise_error):
            self.relay.put(self.test_event)
            self.relay.send()
            self.assertEqual(self.relay.send_queue.qsize(), 0)
            self.assertEqual(self.relay.retry_queue.qsize(), 1)

        # Check that the backoff mechanism tripped.
        self.assertEqual(self.relay.poll_interval, MIN_SESSION_BACKOFF.seconds)

        # Try sending again and ensure that the queues have been drained.
        self.relay.send()
        self.assertEqual(self.relay.send_queue.qsize(), 0)
        self.assertEqual(self.relay.retry_queue.qsize(), 0)

        # We should now be back to our regularly-scheduled polling interval.
        self.assertEqual(self.relay.poll_interval, RELAY_POLL_INTERVAL)

    def test_restore_fid_swap(self):
        # For non-restore operations, the source_fid and data_fid values
        # are identical, and we can keep track of active operations with
        # either one.
        # During restore operations, we don't know the data_fid until
        # after the operation has started (i.e. RUNNING). The tricky part
        # is that when the restore completes, the source_fid is set to
        # data_fid, so unless we do the swap we'll lose track of the
        # operation.
        start_event = '{"event_time": "2014-01-31 02:58:19 -0500", "event_type": "RESTORE_START", "total_bytes": 0, "lustre_path": "boot/vmlinuz-2.6.32-431.3.1.el6.x86_64", "source_fid": "0x200000400:0x13:0x0", "data_fid": "0x200000400:0x13:0x0"}'
        running_event = '{"event_time": "2014-01-31 02:58:19 -0500", "event_type": "RESTORE_RUNNING", "current_bytes": 0, "total_bytes": 4128688, "lustre_path": "boot/vmlinuz-2.6.32-431.3.1.el6.x86_64", "source_fid": "0x200000400:0x13:0x0", "data_fid": "0x200000401:0x1:0x0"}'
        finish_event = '{"event_time": "2014-01-31 02:58:19 -0500", "event_type": "RESTORE_FINISH", "source_fid": "0x200000401:0x1:0x0", "data_fid": "0x200000401:0x1:0x0"}'

        self.assertDictEqual(self.relay.active_operations, {})

        self.relay.put(start_event)
        start_map = {"0x200000400:0x13:0x0": 1142}
        with patch.object(self.relay.client, "post", return_value={"active_operations": start_map}):
            self.relay.send()
        self.assertDictEqual(self.relay.active_operations, start_map)

        self.relay.put(running_event)
        swapped_map = {"0x200000401:0x1:0x0": 1142}
        with patch.object(self.relay.client, "post", return_value={"active_operations": swapped_map}):
            self.relay.send()
        self.assertDictEqual(self.relay.active_operations, swapped_map)

        self.relay.put(finish_event)
        self.relay.send()
        self.assertDictEqual(self.relay.active_operations, {})
