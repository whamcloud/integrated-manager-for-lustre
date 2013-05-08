#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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

from daemon.daemon import set_signal_handlers
from daemon import DaemonContext
from daemon.pidlockfile import PIDLockFile

from chroma_agent.crypto import Crypto
from chroma_agent.plugin_manager import ActionPluginManager, DevicePluginManager
from chroma_agent.agent_client import AgentClient
from chroma_agent.log import daemon_log, daemon_log_setup, console_log_setup

from chroma_agent.store import AgentStore


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


def kill_orphans_of(parent_pid, timeout = 5):
    """
    If a previous instance of the service left its PID file behind (unclean stop) then
    we will see if there are any subprocesses hanging around, and kill them.  This is done
    to avoid e.g. a mkfs from a previous agent instance still being in progress when we
    start another one (imagine restarting chroma-agent during a long format and then clicking
    the format button again in the GUI).

    :param parent_pid: Find orphans from this PID
    :param timeout: Wait this long for orphan processes to respond to SIGKILL
    :return: None
    """
    victims = []
    for pid in [int(pid) for pid in os.listdir('/proc') if pid.isdigit()]:
        try:
            stat = open("/proc/%s/stat" % pid).read().strip()
            pgid = int(stat.split()[4])
            ppid = int(stat.split()[3])
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
        else:
            if int(pgid) == int(parent_pid) and ppid == 1:
                sys.stderr.write("Killing orphan process %s from previous instance %s\n" % (pid, parent_pid))
                victims.append(pid)
                os.kill(pid, signal.SIGKILL)

    n = 0
    while True:
        for pid in victims:
            if not os.path.exists("/proc/%s" % pid):
                sys.stderr.write("Process %s terminated successfully\n")
                victims.remove(pid)

        if victims:
            n += 1

            if n > timeout:
                raise RuntimeError("Failed to kill orphan processes %s after %s seconds" % (victims, timeout))

            time.sleep(1)
        else:
            break


def main():
    """Daemonize and handle unexpected exceptions"""
    parser = argparse.ArgumentParser(description="Whamcloud Chroma Agent")
    parser.add_argument("--foreground", action="store_true")
    parser.add_argument("--publish-zconf", action="store_true")
    parser.add_argument("--pid-file", default = "/var/run/chroma-agent.pid")
    args = parser.parse_args()

    # FIXME: at startup, if there is a PID file hanging around, find any
    # processes which are children of that old PID, and kill them: prevent
    # orphaned processes from an old agent run hanging around where they
    # could cause trouble (think of a 2 hour mkfs)

    if not args.foreground:
        if os.path.exists(args.pid_file):
            pid = None
            try:
                pid = int(open(args.pid_file).read())
                os.kill(pid, 0)
            except (ValueError, OSError, IOError):
                # Not running, delete stale PID file
                sys.stderr.write("Removing stale PID file\n")
                try:
                    os.remove(args.pid_file)
                    os.remove(args.pid_file + ".lock")
                except OSError, e:
                    import errno
                    if e.errno != errno.ENOENT:
                        raise e

                if pid is not None:
                    kill_orphans_of(pid)
            else:
                # Running, we should refuse to run
                raise RuntimeError("Daemon is already running (PID %s)" % pid)
        else:
            if os.path.exists(args.pid_file + ".lock"):
                sys.stderr.write("Removing stale lock file\n")
                os.remove(args.pid_file + ".lock")

        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        context = DaemonContext(pidfile = PIDLockFile(args.pid_file))
        context.open()

        daemon_log_setup()
        console_log_setup()
        daemon_log.info("Starting in the background")
    else:
        context = None
        daemon_log_setup()
        daemon_log.addHandler(logging.StreamHandler())

        console_log_setup()

    try:
        daemon_log.info("Entering main loop")
        conf = AgentStore.get_server_conf()
        if conf is None:
            daemon_log.error("No configuration found (must be registered before running the agent service)")
            return

        agent_client = AgentClient(
            conf['url'] + "message/",
            ActionPluginManager(),
            DevicePluginManager(),
            ServerProperties(),
            Crypto(AgentStore.libdir()))

        def teardown_callback(*args, **kwargs):
            agent_client.stop()
            agent_client.join()

        if not args.foreground:
            set_signal_handlers({signal.SIGTERM: teardown_callback})
        else:
            signal.signal(signal.SIGINT, teardown_callback)

        agent_client.start()
        # Waking-wait to pick up signals
        while not agent_client.stopped.is_set():
            agent_client.stopped.wait(timeout = 10)

        agent_client.join()
    except Exception, e:
        backtrace = '\n'.join(traceback.format_exception(*(sys.exc_info())))
        daemon_log.error("Unhandled exception: %s" % backtrace)

    if context:
        # NB I would rather ensure cleanup by using 'with', but this
        # is python 2.4-compatible code
        context.close()
    daemon_log.info("Terminating")
