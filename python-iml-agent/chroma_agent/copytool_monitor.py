# -*- coding: utf-8 -*-
# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import sys
import errno
import signal
import threading
import Queue
import select
import json

from argparse import ArgumentParser, ArgumentError, Action
from urlparse import urljoin

from chroma_agent import config
from chroma_agent.conf import ENV_PATH
from chroma_agent.crypto import Crypto
from chroma_agent.log import (
    copytool_log,
    copytool_log_setup,
    increase_loglevel,
    decrease_loglevel,
)
from chroma_agent.utils import lsof
from chroma_agent.agent_client import (
    CryptoClient,
    ExceptionCatchingThread,
    HttpError,
    MAX_BYTES_PER_POST,
    MIN_SESSION_BACKOFF,
    MAX_SESSION_BACKOFF,
)
from iml_common.lib.date_time import IMLDateTime
from iml_common.lib.date_time import FixedOffset

READER_SELECT_TIMEOUT = 1.0
RELAY_POLL_INTERVAL = 1
BUFSIZ = os.fpathconf(1, "PC_PIPE_BUF")
COPYTOOL_PROGRESS_INTERVAL = 5  # default 30, increase for snappier UI


class CopytoolException(Exception):
    pass


class FifoReaderConflict(CopytoolException):
    def __init__(self, pids):
        self.pids = pids

    def __str__(self):
        return "Failed to start FIFO reader due to other readers: %s" % ",".join(self.pids)


# NB: There is a distressing amount of similarity with if not outright
# duplication of agent_client.HttpWriter in this class. They are different
# enough that some significant refactoring would be required to allow
# shared code, though.
class CopytoolEventRelay(ExceptionCatchingThread):
    def __init__(self, copytool, client):
        super(CopytoolEventRelay, self).__init__()

        self.stopping = threading.Event()
        self.copytool = copytool
        self.client = client
        self.send_queue = Queue.Queue()
        self.retry_queue = Queue.Queue()
        self.poll_interval = RELAY_POLL_INTERVAL
        self.active_operations = {}

    def put(self, event):
        # OK to call this from a different thread context.
        self.send_queue.put(event)

    def send(self):
        events = []

        envelope = dict(fqdn=self.client.fqdn, copytool=self.copytool.id, events=events)

        envelope_size = len(json.dumps(envelope))
        while True:
            try:
                event = self.retry_queue.get_nowait()
                copytool_log.debug("Got event from retry queue: %s" % event)
            except Queue.Empty:
                try:
                    raw_event = self.send_queue.get_nowait()
                    event = json.loads(raw_event)
                    copytool_log.debug("Got event from send queue: %s" % event)
                except Queue.Empty:
                    break
                except ValueError:
                    copytool_log.error("Invalid JSON: %s" % raw_event)
                    break

            try:
                date = IMLDateTime.parse(event["event_time"])
                event["event_time"] = date.astimezone(tz=FixedOffset(0)).strftime("%Y-%m-%d %H:%M:%S+00:00")
            except ValueError as e:
                copytool_log.error("Invalid event date in event '%s': %s" % (event, e))
                break

            # During restore operations, we don't know the data_fid until
            # after the operation has started (i.e. RUNNING). The tricky part
            # is that when the restore completes, the source_fid is set to
            # data_fid, so unless we do this swap we'll lose track of the
            # operation.
            if "RUNNING" in event["event_type"]:
                if event["source_fid"] in self.active_operations:
                    self.active_operations[event["data_fid"]] = self.active_operations.pop(event["source_fid"])

            if self.active_operations.get(event.get("data_fid", None), None):
                event["active_operation"] = self.active_operations[event["data_fid"]]

            if "FINISH" in event["event_type"]:
                try:
                    del self.active_operations[event["data_fid"]]
                except KeyError:
                    pass

            copytool_log.debug("event: %s" % json.dumps(event))

            event_size = len(json.dumps(event))
            if event_size > MAX_BYTES_PER_POST:
                copytool_log.error("Oversized event dropped: %s" % event)
                break

            if events and event_size > MAX_BYTES_PER_POST - envelope_size:
                copytool_log.info(
                    "Requeueing oversized message "
                    "(%d + %d > %d, %d messages)" % (event_size, envelope_size, MAX_BYTES_PER_POST, len(events))
                )
                self.retry_queue.put(event)
                break

            events.append(event)
            envelope_size += event_size

        if events:
            copytool_log.debug("EventRelay sending %d events" % len(events))
            try:
                data = self.client.post(envelope)
                copytool_log.debug("Got data back from POST: %s" % data)
                try:
                    self.active_operations.update(data["active_operations"])
                except (KeyError, TypeError):
                    pass
                # Reset any backoff delay that might have been added
                self.reset_backoff()
            except HttpError:
                copytool_log.error("Failed to relay events, requeueing")
                for event in envelope["events"]:
                    self.retry_queue.put(event)
                self.backoff()

    def reset_backoff(self):
        self.poll_interval = RELAY_POLL_INTERVAL

    def backoff(self):
        if self.poll_interval == RELAY_POLL_INTERVAL:
            self.poll_interval = MIN_SESSION_BACKOFF.seconds
        else:
            self.poll_interval *= 2
            if self.poll_interval > MAX_SESSION_BACKOFF.seconds:
                self.poll_interval = MAX_SESSION_BACKOFF.seconds

        copytool_log.info("Retry interval increased to %d seconds" % self.poll_interval)

    def _run(self):
        while not self.stopping.is_set():
            self.send()
            self.stopping.wait(timeout=self.poll_interval)

        # One last attempt to drain the queue on the way out
        self.send()

    def stop(self):
        self.stopping.set()


class CopytoolMonitor(ExceptionCatchingThread):
    def __init__(self, client, copytool):
        super(CopytoolMonitor, self).__init__()

        self.stopping = threading.Event()
        self.copytool = copytool
        self.event_relay = CopytoolEventRelay(self.copytool, client)
        self.read_buffer = ""
        self.reader_fd = None

    def open_fifo(self):
        try:
            os.mkfifo(self.copytool.event_fifo)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e

        pids = lsof(file=self.copytool.event_fifo)
        readers = set()
        writers = set()
        for pid, files in pids.items():
            for file, info in files.items():
                if "r" in info["mode"]:
                    readers.add(pid)
                if "w" in info["mode"]:
                    writers.add(pid)

        if readers:
            raise FifoReaderConflict(readers)

        self.reader_fd = os.open(self.copytool.event_fifo, os.O_RDONLY | os.O_NONBLOCK)
        copytool_log.info("Opened %s for reading" % self.copytool.event_fifo)

    def _run(self):
        self.open_fifo()
        self.event_relay.start()

        copytool_log.info("Copytool monitor starting for %s" % self.copytool)

        while not self.stopping.is_set():
            readable, _, _ = select.select([self.reader_fd], [], [], READER_SELECT_TIMEOUT)
            if not readable:
                continue

            data = os.read(self.reader_fd, BUFSIZ)
            if not data:
                copytool_log.warning("Got EOF on FIFO, restarting reader.")
                os.close(self.reader_fd)
                self.open_fifo()
                continue

            self.read_buffer += data
            if "\n" in self.read_buffer:
                tmp = self.read_buffer.split("\n")
                events, self.read_buffer = tmp[:-1], tmp[-1]
                for event in events:
                    self.event_relay.put(event)
                    copytool_log.debug("Put event in relay queue: %s" % event)

        self.event_relay.stop()
        self.event_relay.join()

    def stop(self):
        self.stopping.set()


class Copytool(object):
    def __init__(self, id, index, bin_path, archive_number, filesystem, mountpoint, hsm_arguments):
        self.id = id
        self.index = index
        self.bin_path = bin_path
        self.archive_number = archive_number
        self.filesystem = filesystem
        self.mountpoint = mountpoint
        self.hsm_arguments = hsm_arguments

    def __str__(self):
        return "%s-%s-%s-%s" % (
            os.path.basename(self.bin_path),
            self.filesystem,
            self.archive_number,
            self.index,
        )

    @property
    def event_fifo(self):
        fifo_dir = config.get("settings", "agent")["copytool_fifo_directory"]
        return os.path.join(fifo_dir, "%s-events" % self)

    def as_dict(self):
        return dict(
            id=self.id,
            index=self.index,
            bin_path=self.bin_path,
            archive_number=self.archive_number,
            filesystem=self.filesystem,
            mountpoint=self.mountpoint,
            hsm_arguments=self.hsm_arguments,
        )


class GetCopytoolAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            setattr(namespace, "copytool", Copytool(**config.get("copytools", values)))
        except KeyError:
            raise ArgumentError(self, "Unknown copytool id '%s'" % values)


def main():
    parser = ArgumentParser(description="Integrated Manager for Lustre* software Copytool Monitor")
    parser.add_argument("copytool_id", action=GetCopytoolAction)
    args = parser.parse_args()

    copytool_log_setup()

    try:
        manager_url = urljoin(os.environ["IML_MANAGER_URL"], "agent/copytool_event")
    except KeyError:
        copytool_log.error("No configuration found (must be configured before starting a copytool monitor)")
        sys.exit(1)

    client = CryptoClient(manager_url, Crypto(ENV_PATH))
    monitor = CopytoolMonitor(client, args.copytool)

    def teardown_callback(*args, **kwargs):
        monitor.stop()

    signal.signal(signal.SIGTERM, teardown_callback)
    signal.signal(signal.SIGINT, teardown_callback)
    signal.signal(signal.SIGUSR1, decrease_loglevel)
    signal.signal(signal.SIGUSR2, increase_loglevel)

    try:
        monitor.start()
        while not monitor.stopping.is_set():
            monitor.stopping.wait(timeout=10)

        monitor.join()
    except Exception as e:
        copytool_log.exception()
        sys.stderr.write("Unhandled exception: %s\n" % e)
        sys.exit(1)

    copytool_log.info("Terminating")
