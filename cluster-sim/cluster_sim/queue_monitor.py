#!/usr/bin/env python
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


import json
import argparse
import time
from datetime import datetime
import requests

all_queues_to_monitor = ['agent_lustre_rx',
                         'agent_linux_rx',
                         'jobs',
                         'job_scheduler_notifications',
                         'celery@eagle-48.eagle.hpdd.intel.com.celery.pidbox',              # To monitor this queue this line needs to be updated by hand.
                         'AgentDaemonRpcInterface.requests',
                         'ScanDaemonRpcInterface.requests',
                         'celery',
                         'agent_syslog_rx',
                         'agent_linux_network_rx',
                         'periodic',
                         'agent_action_runner_rx',
                         'PowerControlRpc.requests',
                         'HttpAgentRpc.requests',
                         'agent_tx',
                         'JobSchedulerRpc.requests',
                         'agent_corosync_rx',
                         'HttpAgentRpc.responses_eagle-48.eagle.hpdd.intel.com_10442',      # To monitor this queue this line needs to be updated by hand.
                         'stats']

queues_to_monitor = ['agent_lustre_rx',
                     'agent_tx',
                     'celery',
                     'stats']

#queues_to_monitor = all_queues_to_monitor


def _authenticated_session(url, username, password):
    session = requests.session()
    session.headers = {"Accept": "application/json",
                       "Content-type": "application/json"}
    session.verify = False
    response = session.get("%s/api/session/" % url)
    if not response.ok:
        raise RuntimeError("Failed to open session")
    session.headers['X-CSRFToken'] = response.cookies['csrftoken']
    session.cookies['csrftoken'] = response.cookies['csrftoken']
    session.cookies['sessionid'] = response.cookies['sessionid']

    response = session.post("%s/api/session/" % url, data = json.dumps({'username': username, 'password': password}))
    if not response.ok:
        raise RuntimeError("Failed to authenticate")

    return session


def get_queues(session, url):
    response = session.get(url + "/api/system_status")
    assert response.ok
    return response.json()['rabbitmq']['queues']


parser = argparse.ArgumentParser(description="IML Queue Monitor")
parser.add_argument('--url', required=False, help="Chroma manager URL", default="https://localhost:8000")
parser.add_argument('--username', required=False, help="REST API username", default='admin')
parser.add_argument('--password', required=False, help="REST API password", default='lustre')
parser.add_argument('--colwidth', required=False, help="Width of output columns", default=20)

args = parser.parse_args()

# Change the url, user and password here.
session = _authenticated_session(args.url, args.username, args.password)

print str(datetime.now()) + ": " + "".join([q.ljust(args.colwidth) for q in queues_to_monitor])

while True:
    ts = time.time()

    samples = dict((queue['name'], queue['messages']) for queue in get_queues(session, args.url) if 'messages' in queue)

    message_counts = [str(samples[sample]).ljust(args.colwidth) for sample in queues_to_monitor]

    print str(datetime.now()) + ": " + "".join(message_counts)

    time.sleep(10)
