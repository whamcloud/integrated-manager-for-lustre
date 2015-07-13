#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import os
import threading
import time
import json

from cluster_sim.log import log
from cluster_sim.utils import Persisted
from chroma_agent.copytool_monitor import Copytool as AgentCopytool, COPYTOOL_PROGRESS_INTERVAL


COPYTOOL_LOOP_INTERVAL = 1


class FakeHsmCopytoolThread(threading.Thread):
    """
    Simulate copytool interaction with a Coordinator.
    """
    def __init__(self, wrapper, coordinator):
        super(FakeHsmCopytoolThread, self).__init__()
        self.coordinator = coordinator
        self.wrapper = wrapper
        self._stopping = threading.Event()
        self.fifo = None
        self.last_progress_event = time.time()
        self.started = False

        self.active_requests = {}

    def _open_fifo(self):
        fifo_path = self.wrapper.event_fifo
        self.fifo = open(fifo_path, "w", 1)
        log.debug("Opened %s for write" % fifo_path)

    @property
    def uuid(self):
        return self.wrapper.uuid

    @property
    def mountpoint(self):
        return self.wrapper.copytool.mountpoint

    @property
    def archive_number(self):
        return self.wrapper.copytool.archive_number

    @property
    def max_bandwidth(self):
        # TODO: Fluctuate a bit
        return 12884901888  # 96Gbps -- 12x QDR

    @property
    def available_bandwidth(self):
        return self.max_bandwidth / len(self.active_requests)

    def send_event(self, **event):
        event_time = time.strftime('%Y-%m-%d %T %z', time.localtime())
        event['event_time'] = event_time
        self.fifo.write("%s\n" % json.dumps(event))

    def register(self):
        self.send_event(**dict(
            event_type = 'REGISTER',
            uuid = self.uuid,
            mount_point = self.mountpoint,
            archive = self.archive_number
        ))

    def unregister(self):
        self.send_event(**dict(
            event_type = 'UNREGISTER',
            uuid = self.uuid,
            mount_point = self.mountpoint,
            archive = self.archive_number
        ))

    def start_request(self, request):
        request['current_bytes'] = 0
        self.active_requests[request['fid']] = request
        self.coordinator.start_request(self.uuid, request)

        self.send_event(**dict(
            event_type = "%s_START" % request['action'],
            lustre_path = request['path'],
            total_bytes = request['total_bytes'],
            current_bytes = request['current_bytes'],
            source_fid = request['fid'],
            data_fid = request['fid']
        ))

    def finish_request(self, request):
        self.coordinator.finish_request(self.uuid, request)

        self.send_event(**dict(
            event_type = "%s_FINISH" % request['action'],
            lustre_path = request['path'],
            total_bytes = request['total_bytes'],
            current_bytes = request['current_bytes'],
            source_fid = request['fid'],
            data_fid = request['fid']
        ))

    def progress_active_requests(self):
        completed_requests = []

        now = time.time()
        progress_silence = self.last_progress_event + COPYTOOL_PROGRESS_INTERVAL
        for fid, request in self.active_requests.items():
            # Removes happen pretty quickly -- just fudge it
            if request['action'] == 'REMOVE':
                request['total_bytes'] = (self.max_bandwidth * COPYTOOL_LOOP_INTERVAL) * 2

            request['current_bytes'] += self.available_bandwidth * COPYTOOL_LOOP_INTERVAL
            if request['current_bytes'] >= request['total_bytes']:
                request['current_bytes'] = request['total_bytes']
                self.finish_request(request)
                completed_requests.append(fid)
                continue

            if now > progress_silence:
                self.send_event(**dict(
                    event_type = "%s_RUNNING" % request['action'],
                    lustre_path = request['path'],
                    total_bytes = request['total_bytes'],
                    current_bytes = request['current_bytes'],
                    source_fid = request['fid'],
                    data_fid = request['fid']
                ))

        if now > progress_silence:
            self.last_progress_event = now

        for fid in completed_requests:
            del self.active_requests[fid]

    def run(self):
        self._open_fifo()
        self.register()

        self.started = True

        log.info("Copytool %s started" % self.wrapper.copytool.id)
        while not self._stopping.is_set():
            for request in self.coordinator.get_agent_requests(self.uuid):
                self.start_request(request)

            self.progress_active_requests()

            self._stopping.wait(COPYTOOL_LOOP_INTERVAL)

    def stop(self):
        self._stopping.set()
        self.unregister()


class FakeHsmCopytool(Persisted):
    """
    Simulator wrapper for the AgentCopytool class, which is used to
    represent a real copytool instance. This class adds layers of
    functionality to actually simulate a copytool (including interaction
    with a simulated Coordinator to take/perform HSM actions).
    """
    default_state = {
        'copytool': {}
    }

    def __init__(self, folder, fqdn, **kwargs):
        self.fqdn = fqdn
        self.copytool = AgentCopytool(**kwargs)

        super(FakeHsmCopytool, self).__init__(folder)

        # The coordinator attribute is set by the coordinator after
        # registration.
        self.coordinator = None
        self._lock = threading.RLock()

        self.state['copytool'] = self.copytool.__dict__
        self.state['server'] = fqdn
        self.save()

    def _new_thread(self):
        if not self.coordinator:
            raise RuntimeError("Attempt to start unregistered copytool: %s" % self.id)
        self._thread = FakeHsmCopytoolThread(self, self.coordinator)

    def __str__(self):
        return str(self.copytool)

    @property
    def active_requests(self):
        return len(self._thread.active_requests)

    @property
    def filename(self):
        return "fake_hsm_copytool-%s.json" % self.id

    @property
    def event_fifo(self):
        fifo_dir, fifo = os.path.split(self.copytool.event_fifo)
        return os.path.join(fifo_dir, "%s-%s" % (self.fqdn, fifo))

    @property
    def id(self):
        return self.copytool.id

    @property
    def index(self):
        return self.copytool.index

    @property
    def bin_path(self):
        return self.copytool.bin_path

    @property
    def filesystem(self):
        return self.copytool.filesystem

    @property
    def archive_number(self):
        return self.copytool.archive_number

    def set_uuid(self, uuid):
        with self._lock:
            self.state['uuid'] = uuid
            self.save()

    @property
    def uuid(self):
        with self._lock:
            return self.state['uuid']

    @property
    def running(self):
        try:
            return self._thread.is_alive()
        except AttributeError:
            return False

    def shutdown(self):
        if self.running:
            self.stop()
            self.join()

    def start(self, coordinator):
        log.info("Starting HSM Copytool: %s" % self.id)
        coordinator.register_agent(self)

        self._new_thread()
        self._thread.start()

        # Give the thread time to start up in order to avoid weird races
        # in CI. This will prevent any transitions from the 'started' state
        # until the copytool is truly started.
        startup_timeout = 30  # 5-10 seconds seems typical; pad it out a bit
        while startup_timeout > 0:
            if self._thread.started:
                return
            time.sleep(1)
            startup_timeout -= 1

        raise RuntimeError("Timed out waiting for copytool thread to start")

    def stop(self):
        if self.running:
            log.info("Stopping HSM Copytool: %s" % self.id)
            try:
                self.coordinator.deregister_agent(self)
            except KeyError:
                pass

            try:
                self._thread.stop()
            except AttributeError:
                pass

    def join(self):
        try:
            self._thread.join()
        except AttributeError:
            pass
