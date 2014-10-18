# coding=utf-8
#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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


import argparse
from collections import defaultdict
import json
import logging
import threading
import traceback
import xmlrpclib
import time
import math
import datetime
import os
import requests

from cluster_sim.cli import SIMULATOR_PORT, SimulatorCli

log = logging.getLogger('benchmark')
log.addHandler(logging.FileHandler('benchmark.log'))
log.addHandler(logging.StreamHandler())
log.setLevel(logging.INFO)
for handler in log.handlers:
    handler.setFormatter(logging.Formatter('[%(asctime)s: %(levelname)s/%(name)s] %(message)s'))


class ApiLatencyMonitor(threading.Thread):
    """
    Run this while a benchmark runs to periodically sample the latency
    of API requests to a particular URL.
    """
    def __init__(self, api_client, path):
        super(ApiLatencyMonitor, self).__init__()

        self._api_client = api_client
        self._path = path
        self._stopping = threading.Event()
        self._period = 1
        self.samples = []

    def stop(self):
        self._stopping.set()

    def run(self):
        while not self._stopping.is_set():
            ts = time.time()
            response = self._api_client.GET(self._path)
            response.text  # Ensure that we have received the response, not just been sent a header
            te = time.time()
            if not response.ok:
                log.warning("Error %s sampling %s" % (response.status_code, self._path))
                self.samples.append((ts, None))
            else:
                self.samples.append((ts, te - ts))

            self._stopping.wait(timeout = self._period)

    @property
    def successful_samples(self):
        return [s for s in self.samples if s[1] is not None]

    @property
    def mean(self):
        """
        Return the mean of the latency of all successful requests, or None
        if there are no such samples available.
        """
        if not len(self.successful_samples):
            return None

        total = sum([s[1] for s in self.successful_samples])
        return total / float(len(self.successful_samples))

    @property
    def stderr(self):
        """
        Return the standard error of all successful requests, or None
        if there are no such samples available
        """
        mean = self.mean
        if mean is None:
            return None

        std_dev = math.sqrt((sum([(s[1] - mean) * (s[1] - mean) for s in self.successful_samples]) / float(len(self.successful_samples))))
        return std_dev / math.sqrt(len(self.successful_samples))

    def __str__(self):
        mean = self.mean
        if mean is None:
            return "%.40s: No data"
        else:
            return "%.40s: %2.2f ± %2.2f" % (self._path, mean, self.stderr)


class QueueDepthMonitor(threading.Thread):
    def __init__(self, benchmark):
        super(QueueDepthMonitor, self).__init__()

        self._benchmark = benchmark
        self._stopping = threading.Event()
        self._period = 1
        self.samples = []

    def stop(self):
        self._stopping.set()

    def run(self):
        while not self._stopping.is_set():
            ts = time.time()

            sample = dict((queue['name'], queue['messages']) for queue in self._benchmark.get_queues() if 'messages' in queue)
            sample['_timestamp'] = ts
            self.samples.append(sample)

            self._stopping.wait(timeout=self._period)

    def __str__(self):
        statistics = defaultdict(list)
        for sample in self.samples:
            for name, val in sample.items():
                statistics[name].append(val)
        del statistics['_timestamp']

        report = ["RabbitMQ queue lengths: (avg, min, max)"]
        for name, values in statistics.items():
            average = sum(values) / float(len(values))
            if average:
                report.append("  %40.40s %06.1f %.4d %.4d" % (name, average, min(values), max(values)))
        return os.linesep.join(report)


class Benchmark(object):
    PLUGIN_NAME = 'simulator_controller'

    def __init__(self, args, simulator):
        self.args = args
        self.url = args.url

        self.api_session = self._authenticated_session(args.username, args.password)
        self.simulator = simulator

    def run(self):
        raise NotImplementedError()

    def run_benchmark(self):
        # Check that the plugin for our simulated controllers is loaded
        response = self.GET("/api/storage_resource_class?plugin_name={plugin_name}".format(plugin_name=self.PLUGIN_NAME))
        if not response.json()['objects']:
            raise RuntimeError("simulator_controller plugin not enabled on manager at %s" % self.url)

        # Remove any servers etc on the manager from previous runs
        log.info("Resetting")
        self.reset()

        # Kick off some threads to monitor things in the background
        self._latency_monitors = {}
        for path in ["/api/session/",
                     "/api/volume/",
                     "/api/target/",
                     "/api/host/",
                     "/api/host/?limit=0",
                     "/api/volume/?limit=0",
                     "/api/target/?limit=0"]:
            monitor = self._latency_monitors[path] = ApiLatencyMonitor(self, path)
            monitor.start()

        self._queue_monitor = QueueDepthMonitor(self)
        self._queue_monitor.start()

        # Kick off the benchmark routine itself
        log.info("Starting %s:" % self.__class__.__name__)
        log.info("    %s" % self.run.__doc__)
        ts = time.time()
        try:
            self.run()
        except:
            log.error(traceback.format_exc())
            raise
        finally:
            for monitor in self._latency_monitors.values():
                monitor.stop()
                monitor.join()

            self._queue_monitor.stop()
            self._queue_monitor.join()

            te = time.time()
            log.info("Ran in %.0fs" % (te - ts))
            log.info("API latencies:")
            for path, monitor in sorted(self._latency_monitors.items(), lambda a, b: cmp(a[0], b[0])):
                log.info("  %s" % monitor)

            log.info(self._queue_monitor)

    def get_registration_secret(self, credit_count, duration=None):
        return SimulatorCli()._acquire_token(self.url + "/", self.args.username, self.args.password, credit_count,
                                             duration=duration, preferred_profile='base_managed')

    def GET(self, path, *args, **kwargs):
        return self.api_session.get("%s%s" % (self.url, path), *args, **kwargs)

    def POST(self, path, *args, **kwargs):
        return self.api_session.post("%s%s" % (self.url, path), *args, **kwargs)

    def DELETE(self, path, *args, **kwargs):
        return self.api_session.delete("%s%s" % (self.url, path), *args, **kwargs)

    def reset(self):
        self.simulator.remove_all_servers()
        self._api_flush_servers()
        self._api_flush_controllers()

    def _wait_for_commands(self, command_uris):
        TIMEOUT = 600
        i = 0
        for uri in command_uris:
            while True:
                response = self.GET(uri)
                assert response.ok
                command = response.json()
                if command['complete']:
                    if command['errored'] or command['cancelled']:
                        raise RuntimeError("Command failed: %s" % command)
                    else:
                        break
                else:
                    time.sleep(1)
                    i += 1
                    if i > TIMEOUT:
                        raise RuntimeError("Timeout on %s" % command['message'])

    def _api_flush_controllers(self):
        for resource in self.GET("/api/storage_resource?plugin_name=simulator_controller&class_name=Couplet").json()['objects']:
            response = self.DELETE(resource['resource_uri'])
            assert response.ok

    def _add_controller(self, controller_id):
        response = self.POST("/api/storage_resource/", data=json.dumps({
            'plugin_name': self.PLUGIN_NAME,
            'class_name': 'Couplet',
            'attrs': {
                'controller_id': controller_id
            }
        }))
        assert response.ok

    def _api_flush_servers(self):
        # Avoid trying to remove all the servers at once to work around HYD-1741
        GROUP_SIZE = 4

        host_count = -1
        while host_count:
            command_uris = []
            for host in self.GET("/api/host/", params = {'limit': GROUP_SIZE}).json()['objects']:
                remove_job = [j for j in host['available_jobs'] if j['class_name'] == "ForceRemoveHostJob"][0]
                response = self.POST("/api/command/", data = json.dumps({
                    'message': "Benchmark clearing %s" % host['fqdn'],
                    'jobs': [
                        {
                            'class_name': "ForceRemoveHostJob",
                            'args': remove_job['args']
                        }
                    ]}))
                assert response.ok
                command_uris.append(response.json()['resource_uri'])

            self._wait_for_commands(command_uris)

            response = self.GET("/api/host/", params = {'limit': GROUP_SIZE})
            host_count = response.json()['meta']['total_count']

    def _authenticated_session(self, username, password):
        session = requests.session()
        session.headers = {"Accept": "application/json",
                           "Content-type": "application/json"}
        session.verify = False
        response = session.get("%s/api/session/" % self.url)
        if not response.ok:
            raise RuntimeError("Failed to open session")
        session.headers['X-CSRFToken'] = response.cookies['csrftoken']
        session.cookies['csrftoken'] = response.cookies['csrftoken']
        session.cookies['sessionid'] = response.cookies['sessionid']

        response = session.post("%s/api/session/" % self.url, data = json.dumps({'username': username, 'password': password}))
        if not response.ok:
            raise RuntimeError("Failed to authenticate")

        return session

    def get_queues(self):
        response = self.GET("/api/system_status")
        assert response.ok
        return response.json()['rabbitmq']['queues']

    def _get_queue(self, queue_name):
        queue = [q for q in self.get_queues() if q['name'] == queue_name][0]

        return queue

    def _connection_count(self):
        response = self.GET("/api/system_status")
        assert response.ok

        return len(response.json()['postgres']['pg_stat_activity']['rows'])


class timed(object):
    def __init__(self, tag):
        self.tag = tag

    def __enter__(self):
        self.ts = time.time()

    def __exit__(self, *args):
        te = time.time()

        log.info("%s: %2.2fs" % (self.tag, te - self.ts))


class FilesystemSizeLimit(Benchmark):
    def run(self):
        """Create increasingly large filesystems on large numbers of server and controllers until an error occurs."""

        SU_SIZE = 4

        log.debug("Connection count initially: %s" % self._connection_count())
        n = self.args.servers
        VOLUMES_PER_SERVER = 4
        while True:
            ost_count = (n * VOLUMES_PER_SERVER - 2)
            log.info("n = %s (ost count = %s)" % (n, ost_count))

            secret = self.get_registration_secret(n, datetime.timedelta(seconds=3600))
            command_uris = []
            fqdns = []
            serials = []
            log.debug("Creating servers...")
            for i in range(0, n, SU_SIZE):
                su_result = self.simulator.add_su(SU_SIZE, SU_SIZE * VOLUMES_PER_SERVER, 1)
                fqdns.extend(su_result['fqdns'])
                serials.extend(su_result['serials'])
                self._add_controller(su_result['controller_id'])

            log.debug("Registering servers...")
            for fqdn in fqdns:
                registration_result = self.simulator.register(fqdn, secret)
                command_uris.append("/api/command/%s/" % (registration_result['command_id']))

            log.debug("Waiting for setup...")
            with timed("Setup commands for %s servers" % n):
                try:
                    self._wait_for_commands(command_uris)
                except RuntimeError, e:
                    log.error("Failed registering %s servers: %s" % (n, e))
                    log.error("Connection count: %s" % self._connection_count())
                    break

            # Resolve serials to volume IDs
            response = self.GET("/api/volume/", params = {'limit': 0})
            assert response.ok
            serial_to_id = {}
            for volume in response.json()['objects']:
                serial_to_id[volume['label']] = volume['id']

            log.debug("Requesting filesystem creation...")

            with timed("Filesystem creation POST (%d OSTs)" % ost_count):
                response = self.POST("/api/filesystem/",
                                                 data=json.dumps({
                                                     'name': 'testfs',
                                                     'mgt': {'volume_id': serial_to_id[serials[0]]},
                                                     'mdt': {
                                                         'volume_id': serial_to_id[serials[1]],
                                                         'conf_params': {}
                                                     },
                                                     'osts': [
                                                         {
                                                             'volume_id': v_id,
                                                             'conf_params': {}
                                                         } for v_id in [serial_to_id[serial] for serial in serials[2:]]],
                                                     'conf_params': {}
                                                 })
                                                 )
                if not response.ok:
                    log.error(response.text)
                assert response.ok
                command_uri = response.json()['command']['resource_uri']

            log.debug("Awaiting filesystem creation...")
            assert response.status_code == 202, response.status_code
            self._wait_for_commands([command_uri])

            log.info("Success for n = %s" % n)
            n += self.args.servers


class ConcurrentRegistrationLimit(Benchmark):
    def run(self):
        """
        Increase the number of concurrent server registrations until server
        setup commands start failing.

        What we're testing here is that not only can N servers exist, but that
        they can all register at the same instant without causing anything to fall over.
        """
        SU_SIZE = 4

        log.debug("Connection count initially: %s" % self._connection_count())
        n = self.args.servers
        while True:
            log.info("n = %s" % n)

            command_uris = []

            secret = self.get_registration_secret(n, duration = datetime.timedelta(seconds = 3600))

            fqdns = []
            for i in range(0, n, SU_SIZE):
                fqdns.extend(self.simulator.add_su(SU_SIZE, SU_SIZE * 2, 1)['fqdns'])

            registration_results = self.simulator.register_many(fqdns, secret)
            for result in registration_results:
                command_uris.append("/api/command/%s/" % (result['command_id']))

            try:
                self._wait_for_commands(command_uris)
            except RuntimeError, e:
                log.error("Failed registering %s servers: %s" % (n, e))
                log.debug("Connection count: %s" % self._connection_count())
                break
            else:
                log.info("Success registering %s servers" % n)
                log.debug("Connection count: %s" % self._connection_count())
                self.reset()
                log.debug("Connection count after flush: %s" % self._connection_count())
                n += self.args.servers


class ServerCountLimit(Benchmark):
    def run(self):
        """
        Increase the number of servers being monitored until queues start backing up
        """
        # Some arbitrary nonzero amount of log data from each server
        LOG_RATE = 10

        add_group_size = 4
        volumes_per_server = 4
        i = 0
        baseline = dict((queue['name'], queue['messages']) for queue in self.get_queues())
        while True:
            log.info("i = %s, adding %s servers" % (i, add_group_size))
            time.sleep(1)
            registration_command_uris = []
            i += add_group_size
            result = self.simulator.add_su(add_group_size, add_group_size * volumes_per_server, 1)
            for fqdn in result['fqdns']:
                self.simulator.set_log_rate(fqdn, LOG_RATE)
                secret = self.get_registration_secret(1)
                result = self.simulator.register(fqdn, secret)
                registration_command_uris.append('/api/command/%s/' % (result['command_id']))
            self._wait_for_commands(registration_command_uris)

            backed_up_queues = []
            for queue in self.get_queues():
                if queue['messages'] - baseline.get(queue['name'], 0) > max(queue['message_stats_ack_details_rate'], i):
                    backed_up_queues.append(queue['name'])
                    log.info("Queue %s is backed up (%s-%s>%s in=%.2f out=%.2f)" % (
                        queue['name'],
                        queue['messages'],
                        baseline.get(queue['name'], 0),
                        max(queue['message_stats_ack_details_rate'], i),
                        queue['message_stats_publish_details_rate'],
                        queue['message_stats_ack_details_rate']))

            if backed_up_queues:
                break

            # TODO: additional check: that there are no contact alerts
            # TODO: additional check: periodically, that we can stop and start lnet
            # on each server with a sensible latency (responsiveness to actions)


class LogIngestRate(Benchmark):
    def run(self):
        """Increase the rate of log messages from a fixed number of servers until the
        log RX queue starts to back up"""
        # Actual log messages per second is (log_rate / Session.POLL_INTERVAL) * server_count
        server_count = self.args.servers

        server_fqdns = []
        registration_command_uris = []
        for n in range(0, server_count):
            fqdn = self.simulator.add_server(1)
            secret = self.get_registration_secret(1)
            result = self.simulator.register(fqdn, secret)
            server_fqdns.append(fqdn)
            registration_command_uris.append("/api/command/%s/" % (result['command_id']))

        self._wait_for_commands(registration_command_uris)

        response = self.GET("/api/log/")
        assert response.ok
        log_message_count = response.json()['meta']['total_count']
        log.debug("Initially DB contains %s log messages" % log_message_count)

        tap_out = 0
        saturated_samples = []
        log_rate = 8
        while True:
            log.info("log_rate = %s" % log_rate)
            for fqdn in server_fqdns:
                self.simulator.set_log_rate(fqdn, log_rate)

            time.sleep(10)

            syslog_queue = self._get_queue('agent_syslog_rx')
            if syslog_queue['messages'] > max(syslog_queue['message_stats_ack_details_rate'] * 4, server_count):
                tap_out += 1
                if tap_out > 0:
                    saturated_samples.append(syslog_queue['message_stats_publish_details_rate'])
                if tap_out >= 3:
                    log.warning("Stayed backed up for %s iterations, breaking" % tap_out)
                    break
            else:
                tap_out = 0
                saturated_samples = []
                log_rate *= 2

        log.debug("Stopping log generation")
        for n in range(0, 8):
            self.simulator.set_log_rate('test%.3d.localdomain' % n, 0)

        log.debug("Waiting for queue to drain")
        rate_samples = []
        while True:
            syslog_queue = self._get_queue('agent_syslog_rx')
            log.debug(syslog_queue['messages'], syslog_queue['message_stats_ack_details_rate'])

            if syslog_queue['messages'] == 0:
                log.info("Finish draining")
                break
            else:
                rate_samples.append(syslog_queue['message_stats_ack_details_rate'])

            time.sleep(5)

        avg = sum(rate_samples) / float(len(rate_samples))
        std_dev = math.sqrt((sum([(s - avg) * (s - avg) for s in rate_samples]) / float(len(rate_samples))))
        std_err = std_dev / math.sqrt(len(rate_samples))

        log.info("%s +/- %s" % (avg, std_err))
        # Convert message rate to log line rate
        from chroma_agent.device_plugins.syslog import MAX_LOG_LINES_PER_MESSAGE
        log.info("%s +/- %s" % (avg * MAX_LOG_LINES_PER_MESSAGE, std_err * MAX_LOG_LINES_PER_MESSAGE))

        # FIXME: try running this with syslog DB writing disabled, such that rabbitmq is the bottleneck, and you
        # can get messages to back up on the agent side, using up unbounded memory: the rabbitmq part never backs up
        # so the benchmark never stops!

        # FIXME: populate the db with some targets and NIDs and include them in the incoming log messages


def main():
    parser = argparse.ArgumentParser(description="Simulated benchmarks")
    parser.add_argument('--remote_simulator', required=False, help="Disable built-in simulator (run it separately)", default=False)
    parser.add_argument('--debug', required=False, help="Enable DEBUG-level logs", default=False)
    parser.add_argument('--url', required=False, help="Chroma manager URL", default="https://localhost:8000")
    parser.add_argument('--username', required=False, help="REST API username", default='debug')
    parser.add_argument('--password', required=False, help="REST API password", default='chr0m4_d3bug')
    parser.add_argument('--servers', help="server count", default=8, type=int)
    subparsers = parser.add_subparsers()

    log_ingest_parser = subparsers.add_parser("reset")
    log_ingest_parser.set_defaults(func=lambda args, simulator: Benchmark(args, simulator).reset())

    log_ingest_parser = subparsers.add_parser("log_ingest_rate")
    log_ingest_parser.set_defaults(func=lambda args, simulator: LogIngestRate(args, simulator).run_benchmark())

    server_count_limit_parser = subparsers.add_parser("server_count_limit")
    server_count_limit_parser.set_defaults(func=lambda args, simulator: ServerCountLimit(args, simulator).run_benchmark())

    server_count_limit_parser = subparsers.add_parser("concurrent_registration_limit")
    server_count_limit_parser.set_defaults(func=lambda args, simulator: ConcurrentRegistrationLimit(args, simulator).run_benchmark())

    server_count_limit_parser = subparsers.add_parser("filesystem_size_limit")
    server_count_limit_parser.set_defaults(func=lambda args, simulator: FilesystemSizeLimit(args, simulator).run_benchmark())

    args = parser.parse_args()

    if args.debug:
        log.setLevel(logging.DEBUG)

    if not args.remote_simulator:
        log.info("Starting simulator...")

        # Enable logging by agent code run within simulator
        from chroma_agent.log import daemon_log
        daemon_log.setLevel(logging.DEBUG)
        handler = logging.FileHandler("chroma-agent.log")
        handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
        daemon_log.addHandler(handler)
        daemon_log.info("Enabled agent logging within simulator")

        from cluster_sim.simulator import ClusterSimulator
        simulator = ClusterSimulator(folder=None, url=args.url + "/")
        simulator.power.setup(1)
        simulator.start_all()
        simulator.setup(0, 0, 0, nid_count=1, cluster_size=4, pdu_count=1, su_size=0)
    else:
        simulator = xmlrpclib.ServerProxy("http://localhost:%s" % SIMULATOR_PORT, allow_none=True)

    try:
        log.info("Starting benchmark...")
        args.func(args, simulator)
    except:
        # Because we do a hard exit at the end here, explicitly log terminating
        # exceptions or they would get lost.
        log.error(traceback.format_exc())
        raise
    finally:
        # Do a hard exit to avoid dealing with lingering threads (not the cleanest, but
        # this isn't production code).
        os._exit(-1)

    log.info("Complete.")
