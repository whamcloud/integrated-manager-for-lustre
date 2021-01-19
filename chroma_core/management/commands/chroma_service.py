# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import threading
import sys
import signal
import linecache
from chroma_core.services import ServiceThread
import os

# PIDLockFile was split out of daemon into it's own package in daemon-1.6
try:
    from daemon.pidlockfile import PIDLockFile

    assert PIDLockFile  # Silence Pyflakes
except ImportError:
    from lockfile.pidlockfile import PIDLockFile

from daemon import DaemonContext
from django.core.management.base import BaseCommand
from chroma_core.services.log import log_set_filename, log_register, log_enable_stdout
from chroma_core.services.rpc import RpcClientFactory
from emf_common.lib.date_time import EMFDateTime
import chroma_core.services.log


log = log_register(__name__.split(".")[-1])


class Command(BaseCommand):
    requires_model_validation = False
    help = """Run a single ChromaService in a new plugin."""

    def add_arguments(self, parser):
        parser.add_argument("services", nargs="+", type=str)
        parser.add_argument("--gevent", action="store_true", dest="gevent", default=False)
        parser.add_argument("--lightweight-rpc", action="store_true", dest="lightweight_rpc", default=False)
        parser.add_argument("--verbose", action="store_true", dest="verbose", default=False)
        parser.add_argument("--console", action="store_true", dest="console", default=False)
        parser.add_argument("--name", dest="name", default="chroma_service")
        parser.add_argument("--daemon", dest="daemon", action="store_true", default=None)
        parser.add_argument("--trace", dest="trace", action="store_true", default=None)
        parser.add_argument("--pid-file", dest="pid-file", default=None)

    def execute(self, *args, **options):
        if options["daemon"]:
            pid_file = options["pid-file"]
            if os.path.exists(pid_file + ".lock") or os.path.exists(pid_file):
                try:
                    pid = int(open(pid_file).read())
                    os.kill(pid, 0)
                except (ValueError, OSError, IOError):
                    # Not running, delete stale PID file
                    sys.stderr.write("Removing stale PID file\n")
                    import errno

                    try:
                        os.remove(pid_file)
                    except OSError as e:
                        if e.errno != errno.ENOENT:
                            raise e
                    try:
                        os.remove(pid_file + ".lock")
                    except OSError as e:
                        if e.errno != errno.ENOENT:
                            raise e
                else:
                    # Running, we should refuse to run
                    raise RuntimeError("Daemon is already running (PID %s)" % pid)

            with DaemonContext(pidfile=PIDLockFile(pid_file)):
                self._execute_inner(*args, **options)
        else:
            self._execute_inner(*args, **options)

    def _execute_inner(self, *args, **options):
        if options["verbose"]:
            log_enable_stdout()

        if options["console"]:
            log_enable_stdout()
        else:
            log_set_filename("%s.log" % options["name"])

        if options["gevent"]:
            from gevent.monkey import patch_all

            patch_all(thread=True)
            # Gevent's implementation of select removes 'poll'
            import subprocess

            subprocess._has_poll = False

            import django.db

            django.db.connections._connections = threading.local()

        if options["trace"]:

            class Trace(object):
                def __init__(self):
                    self.tracefile = open("trace.log", "w", buffering=0)
                    self.tracefile.write("Started at %s: %s %s\n" % (EMFDateTime.utcnow(), args, options))

                def __call__(self, frame, event, arg):
                    if event == "line":
                        try:
                            pyfile = frame.f_globals["__file__"].strip("co")
                            line = linecache.getline(pyfile, frame.f_lineno)
                        except KeyError:
                            pass
                        else:
                            if line is not None:
                                self.tracefile.write("%s:%s %s" % (pyfile, frame.f_lineno, line))

                    return self

            chroma_core.services.log.trace = Trace()
            sys.settrace(chroma_core.services.log.trace)

        from chroma_core.lib.service_config import ServiceConfig

        if not ServiceConfig().configured():
            sys.stderr.write("EMF is not configured, please run chroma-config setup first\n")
            sys.exit(-1)

        if not options["lightweight_rpc"]:
            RpcClientFactory.initialize_threads()

        # Respond to Ctrl+C
        stopped = threading.Event()

        # Ensure that threads are .start()ed before we possibly try to .join() them
        setup_complete = threading.Event()

        """
           Params undefined because gevent vs. threading pass
           different things to handler
        """

        def signal_handler(*args, **kwargs):
            if not setup_complete.is_set():
                log.warning("Terminated during setup, exiting hard")
                os._exit(0)

            if not options["lightweight_rpc"]:
                RpcClientFactory.shutdown_threads()

            for service_thread in service_mains:
                log.info("Stopping %s" % service_thread.service.name)
                service_thread.service.stop()

            for service_thread in service_mains:
                log.info("Joining %s" % service_thread.service.name)
                service_thread.join()

            stopped.set()

        if options["gevent"]:
            import gevent

            gevent.signal(signal.SIGINT, signal_handler)
            gevent.signal(signal.SIGTERM, signal_handler)
        else:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

        service_mains = []
        for service_name in options["services"]:
            module_path = "chroma_core.services.%s" % service_name

            # Load the module
            mod = __import__(module_path)
            components = module_path.split(".")
            for comp in components[1:]:
                mod = getattr(mod, comp)

            service = getattr(mod, "Service")()
            service.log = log_register(service.name)

            service_thread = ServiceThread(service)
            service_thread.start()
            service_mains.append(service_thread)

        setup_complete.set()

        while not stopped.is_set():
            # Using a timeout changes the behaviour of CPython's waiting so that it will
            # receive signals (like ctrl-c SIGINT) immediately -- logically we don't want
            # any timeout here, but a pure wait() breaks ctrl-c.
            stopped.wait(10)

        if len(threading.enumerate()) > 1 and not options["gevent"]:
            log.error("Rogue thread still running, exiting hard")
            log.error([t.name for t in threading.enumerate()])
            os._exit(-1)
