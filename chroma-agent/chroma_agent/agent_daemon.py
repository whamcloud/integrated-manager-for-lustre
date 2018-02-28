# -*- coding: utf-8 -*-
# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import time
import datetime
import errno
import os
import logging
import sys
import traceback
import argparse
import signal
import socket

from chroma_agent import config
from chroma_agent.crypto import Crypto
from chroma_agent.plugin_manager import ActionPluginManager, DevicePluginManager
from chroma_agent.agent_client import AgentClient
from chroma_agent.log import daemon_log, daemon_log_setup, console_log_setup, increase_loglevel, decrease_loglevel
from chroma_agent.lib.agent_startup_functions import agent_daemon_startup_functions
from chroma_agent.lib.agent_teardown_functions import agent_daemon_teardown_functions

# Disable insecure requests warning
# So we don't break our syslog handler.
# This (disabled) warning is expected due to our use of 
# self-signed certificates when we communicate between
# the agent and manager.
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ServerProperties(object):
    @property
    def fqdn(self):
        return socket.getfqdn()

    @property
    def nodename(self):
        return os.uname()[1]

    @property
    def boot_time(self):
        for line in open("/proc/stat").readlines():
            name, val = line.split(" ", 1)
            if name == 'btime':
                return datetime.datetime.fromtimestamp(int(val))


def main():
    """handle unexpected exceptions"""
    parser = argparse.ArgumentParser(
        description="Intel® Manager for Lustre* software Agent")

    parser.add_argument("--publish-zconf", action="store_true")
    args = parser.parse_args()

    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    daemon_log_setup()
    console_log_setup()
    daemon_log.info("Starting")

    try:
        daemon_log.info("Entering main loop")
        try:
            conf = config.get('settings', 'server')
        except (KeyError, TypeError) as e:
            daemon_log.error(
                "No configuration found (must be registered before running the agent service), "
                "details: %s" % e)
            return

        if config.profile_managed is False:
            # This is kind of terrible. The design of DevicePluginManager is
            # such that it can be called with either class methods or
            # instantiated and then called with instance methods. As such,
            # we can't pass in a list of excluded plugins to the instance
            # constructor. Well, we could, but it would only work some
            # of the time and that would be even more awful.
            import chroma_agent.plugin_manager
            chroma_agent.plugin_manager.EXCLUDED_PLUGINS += ['corosync']

        agent_client = AgentClient(conf['url'] + "message/",
                                   ActionPluginManager(),
                                   DevicePluginManager(), ServerProperties(),
                                   Crypto(config.path))

        def teardown_callback(*args, **kwargs):
            agent_client.stop()
            agent_client.join()
            [function() for function in agent_daemon_teardown_functions]

        signal.signal(signal.SIGINT, teardown_callback)
        signal.signal(signal.SIGTERM, teardown_callback)
        signal.signal(signal.SIGUSR1, decrease_loglevel)
        signal.signal(signal.SIGUSR2, increase_loglevel)

        # Call any agent daemon startup methods that were registered.
        [function() for function in agent_daemon_startup_functions]

        agent_client.start()
        # Waking-wait to pick up signals
        while not agent_client.stopped.is_set():
            agent_client.stopped.wait(timeout=10)

        agent_client.join()
    except Exception, e:
        backtrace = '\n'.join(traceback.format_exception(*(sys.exc_info())))
        daemon_log.error("Unhandled exception: %s" % backtrace)

    # Call any agent daemon teardown methods that were registered.
    [function() for function in agent_daemon_teardown_functions]

    daemon_log.info("Terminating")
