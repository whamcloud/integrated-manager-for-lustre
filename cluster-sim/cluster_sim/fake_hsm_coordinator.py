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
import random
import threading
import time
import uuid
import Queue
from collections import defaultdict

from cluster_sim.log import log
from cluster_sim.utils import Persisted


HSM_COORDINATOR_LOOP_INTERVAL = 10


class FakeHsmCoordinatorThread(threading.Thread):
    MAX_REQUESTS_PER_COPYTOOL = 3

    def __init__(self, coordinator):
        super(FakeHsmCoordinatorThread, self).__init__()

        self._lock = threading.Lock()
        self._stopping = threading.Event()
        self.coordinator = coordinator

        self.unassigned_requests = Queue.Queue()
        self.agent_requests = defaultdict(Queue.Queue)
        self.active_requests = defaultdict(dict)
        self.complete_requests = {}

    def get_random_path(self):
        PATH_COMPONENTS = ['project', 'plan', 'datasets', 'databases', 'catalogs', 'research', 'investigator', 'data', 'files', 'library', 'libs', 'spool', 'scratch', 'backup', 'notbackedup']
        FILENAMES = ['index', 'file', 'db', 'database', 'catalog', 'data', 'cabinet']
        SUFFIXES = ['', '.tar', '.tar.gz', '.tar.bz2', '.idx', '.cab', '.db']

        directory = os.path.join(*[random.choice(PATH_COMPONENTS)] + [path for path in PATH_COMPONENTS if bool(random.getrandbits(1))])
        return os.path.join(directory, random.choice(FILENAMES) + random.choice(SUFFIXES))

    def get_random_size(self):
        MIN_FILESIZE = 1024
        MAX_FILESIZE = 2 ** 41  # 2TB
        MODE = MAX_FILESIZE * .025  # cluster around 51GB

        return int(random.triangular(MIN_FILESIZE, MAX_FILESIZE, MODE))

    def get_random_fid(self):
        return "0x%09x:0x%x:0x%x" % (random.randint(1, 2 ** 33),
                                     random.randint(1, 2), 0)

    def get_random_action(self):
        ACTIONS = ['ARCHIVE', 'RESTORE', 'REMOVE']

        return dict(
            action = random.choice(ACTIONS),
            path = self.get_random_path(),
            total_bytes = self.get_random_size(),
            fid = self.get_random_fid()
        )

    def agent_request_count(self, agent_uuid):
        request_count = 0
        try:
            request_count += self.agent_requests[agent_uuid].qsize()
        except KeyError:
            pass
        try:
            request_count += len(self.active_requests[agent_uuid])
        except KeyError:
            pass
        return request_count

    def purge_agent_requests(self, agent_uuid):
        try:
            del self.agent_requests[agent_uuid]
        except KeyError:
            pass

        try:
            del self.active_requests[agent_uuid]
        except KeyError:
            pass

    def generate_actions_for_agents(self):
        for agent in self.coordinator.agents:
            while self.agent_request_count(agent.uuid) < self.MAX_REQUESTS_PER_COPYTOOL:
                try:
                    action = self.unassigned_requests.get_nowait()
                    log.debug("Took %s from unassigned: %d" % (action, self.unassigned_requests.qsize()))
                except Queue.Empty:
                    action = self.get_random_action()
                    log.debug("Got random action: %s" % action)
                self.agent_requests[agent.uuid].put(action)

    def start_request(self, agent_uuid, request):
        fid = request['fid']
        if fid in self.active_requests[agent_uuid]:
            log.error("Received duplicate start request %s for %s" % (request, fid))
            return

        self.active_requests[agent_uuid][fid] = request

    def finish_request(self, agent_uuid, request):
        fid = request['fid']
        try:
            del self.active_requests[agent_uuid][fid]
        except KeyError:
            log.error("Received finish request %s for unknown action on %s" % (request, fid))
            return

        request['completed_at'] = time.time()
        self.complete_requests[fid] = request

    def cull_completed_requests(self):
        start = self.complete_request_count
        cutoff = time.time() - 5 * 60
        culls = [f for f, r in self.complete_requests.items() if r['completed_at'] < cutoff]

        for fid in culls:
            del self.complete_requests[fid]

        culled = start - self.complete_request_count
        if culled:
            log.debug("Culled %d completed requests" % culled)

    @property
    def waiting_request_count(self):
        return (self.unassigned_requests.qsize()
                + sum([q.qsize() for q in self.agent_requests.values()]))

    @property
    def running_request_count(self):
        return sum([len(v) for v in self.active_requests.values()])

    @property
    def complete_request_count(self):
        return len(self.complete_requests)

    def stop(self):
        log.debug("Coordinator thread for %s stopping" % self.coordinator.filesystem)
        self._stopping.set()

    def run(self):
        if not self.coordinator.enabled:
            return

        log.debug("Coordinator thread for %s starting: %s" %
                  (self.coordinator.filesystem, threading.current_thread()))

        while not self._stopping.is_set():
            # Keep agents busy
            self.generate_actions_for_agents()

            # Stack up waiting actions
            if bool(random.getrandbits(1)):
                self.unassigned_requests.put(self.get_random_action())

            self.cull_completed_requests()

            # TODO: Very infrequently, randomly cancel an agent action

            self._stopping.wait(HSM_COORDINATOR_LOOP_INTERVAL)


class FakeHsmCoordinator(Persisted):
    default_state = {
        'enabled': False,
    }

    control_map = {
        'enabled': "enable",
        'shutdown': "shutdown",
        'disabled': "disable",
        'purge': "purge"
    }

    def __init__(self, simulator, filesystem, mdt=None):
        self.filesystem = filesystem
        self.simulator = simulator

        # Don't persist the set of registered agents -- they'll get
        # re-registered on process start.
        self.registered_agents = {}

        super(FakeHsmCoordinator, self).__init__(simulator.folder)

        self._lock = threading.RLock()
        self._new_thread()

        self.state['filesystem'] = filesystem
        if not mdt:
            mdt = 'MDT0000'
        self.state['mdt'] = mdt
        self.save()

    def _new_thread(self):
        self._thread = FakeHsmCoordinatorThread(self)

    @property
    def agents(self):
        with self._lock:
            return self.registered_agents.values()

    def get_agent_by_id(self, agent_id):
        with self._lock:
            try:
                return [a for a in self.registered_agents.values()
                        if a.id == agent_id][0]
            except IndexError:
                log.error("Cannot find unknown agent by id: %s" % agent_id)
                raise

    def register_agent(self, agent):
        try:
            exists = self.get_agent_by_id(agent.id)
            log.warn("Deregistering existing agent with id %s" % exists.id)
            self.deregister_agent(exists.id)
        except IndexError:
            pass

        with self._lock:
            agent.set_uuid(str(uuid.uuid4()))
            agent.coordinator = self
            self.registered_agents[agent.uuid] = agent
            log.info("Registered agent: %s (%s)" % (agent.id, agent.uuid))

    def deregister_agent(self, agent):
        with self._lock:
            del self.registered_agents[agent.uuid]
            self._thread.purge_agent_requests(agent.uuid)
            log.info("Deregistered agent: %s" % agent.id)

    @property
    def agent_stats(self):
        stats = {
            'total': 0,
            'idle': 0,
            'busy': 0
        }

        for agent in self.agents:
            stats['total'] += 1
            if not agent.active_requests:
                stats['idle'] += 1
            else:
                stats['busy'] += 1

        return stats

    @property
    def action_stats(self):
        stats = {
            'waiting': self._thread.waiting_request_count,
            'running': self._thread.running_request_count,
            'succeeded': self._thread.complete_request_count,
            'errored': 0
        }

        return stats

    @property
    def hsm_stats(self):
        if not self.enabled:
            return {}

        return {
            'hsm': {
                'agents': self.agent_stats,
                'actions': self.action_stats
            }
        }

    @property
    def mdt(self):
        return "%s-%s" % (self.state['filesystem'], self.state['mdt'])

    @property
    def filename(self):
        return "fake_hsm_coordinator-%s.json" % self.filesystem

    @property
    def enabled(self):
        with self._lock:
            return self.state['enabled']

    @property
    def running(self):
        return self._thread.is_alive()

    def get_agent_requests(self, agent_uuid):
        while True:
            try:
                yield self._thread.agent_requests[agent_uuid].get_nowait()
            except (KeyError, Queue.Empty):
                break

    def start_request(self, agent_uuid, request):
        log.debug("Got start on %s from %s" % (request, agent_uuid))
        self._thread.start_request(agent_uuid, request)

    def finish_request(self, agent_uuid, request):
        log.debug("Got finish on %s from %s" % (request, agent_uuid))
        self._thread.finish_request(agent_uuid, request)

    def enable(self):
        if self.running:
            return

        with self._lock:
            self.state['enabled'] = True
            self.save()

        if not self.running:
            self._new_thread()
            self._thread.start()

    def disable(self):
        if self.running:
            self.shutdown()

        with self._lock:
            self.state['enabled'] = False
            self.save()

    def shutdown(self):
        if self.running:
            self.stop()
            self.join()

    def purge(self):
        self.disable()

        with self._lock:
            for request in self.active_requests:
                request.cancel()

            self.save()

        self.enable()

    def control(self, control_value):
        if not control_value in self.control_map:
            raise RuntimeError("Unknown HSM Coordinator control value: %s"
                               % control_value)

        getattr(self, self.control_map[control_value])()

    def start(self):
        if self.enabled:
            log.info("Starting HSM Coordinator for %s" % self.mdt)
            self._new_thread()
            self._thread.start()

    def stop(self):
        if self.running:
            log.info("Stopping HSM Coordinator for %s" % self.mdt)
            self._thread.stop()

    def join(self):
        self._thread.join()
