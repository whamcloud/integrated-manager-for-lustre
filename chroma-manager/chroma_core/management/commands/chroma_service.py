    #
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from optparse import make_option

import threading
import sys
import traceback
import signal
import os
from daemon.pidlockfile import PIDLockFile
from daemon import DaemonContext
from django.core.management.base import BaseCommand
from chroma_core.services.log import log_set_filename, log_register, log_enable_stdout
from chroma_core.services.rpc import RpcClientFactory


log = log_register(__name__.split('.')[-1])


class ServiceMain(threading.Thread):
    """Given a ChromaService instance, execute its start() method, logging any
    exception thrown"""
    def __init__(self, service, *args, **kwargs):
        super(ServiceMain, self).__init__(*args, **kwargs)
        self.service = service

    def run(self):
        service_name = self.service.__class__.__module__.split('.')[-1]
        self.service.log = log_register(service_name)
        try:
            log.info("Running %s" % service_name)
            self.service.start()
        except Exception:
            exc_info = sys.exc_info()
            backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
            log.warning("Exception from run_main_loop.  backtrace: %s" % backtrace)


class Command(BaseCommand):
    help = """Run a single ChromaService in a new plugin."""
    option_list = BaseCommand.option_list + (
        make_option('--gevent', action = 'store_true', dest = 'gevent', default = False),
        make_option('--lightweight-rpc', action = 'store_true', dest = 'lightweight_rpc', default = False),
        make_option('--verbose', action = 'store_true', dest = 'verbose', default = False),
        make_option('--name', dest = 'name', default = 'chroma_service'),
        make_option('--daemon', dest = 'daemon', action = 'store_true', default = None),
        make_option('--pid-file', dest = 'pid-file', default = None),
    )

    def execute(self, *args, **options):
        if options['daemon']:
            pid_file = options['pid-file']
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
                    except OSError, e:
                        if e.errno != errno.ENOENT:
                            raise e
                    try:
                        os.remove(pid_file + ".lock")
                    except OSError, e:
                        if e.errno != errno.ENOENT:
                            raise e
                else:
                    # Running, we should refuse to run
                    raise RuntimeError("Daemon is already running (PID %s)" % pid)

            with DaemonContext(pidfile = PIDLockFile(pid_file)):
                self._execute_inner(*args, **options)
        else:
            self._execute_inner(*args, **options)

    def _execute_inner(self, *args, **options):
        if options['verbose']:
            log_enable_stdout()

        if options['gevent']:
            from gevent.monkey import patch_all
            patch_all()

        from chroma_core.lib.service_config import ServiceConfig
        if not ServiceConfig().configured():
            sys.stderr.write("Chroma is not configured, please run chroma-config setup first\n")
            sys.exit(-1)

        if not options['lightweight_rpc']:
            RpcClientFactory.initialize_threads()

        log_set_filename("%s.log" % options['name'])

        # Respond to Ctrl+C
        stopped = threading.Event()

        def signal_handler(*args, **kwargs):
            """Params undefined because gevent vs. threading pass
            different things to handler

            """
            for service_thread in service_mains:
                log.info("Stopping %s" % service_thread.service.__class__.__name__)
                service_thread.service.stop()

            for service_thread in service_mains:
                log.info("Joining %s" % service_thread.service.__class__.__name__)
                service_thread.join()

            stopped.set()

        if options['gevent']:
            import gevent
            gevent.signal(signal.SIGINT, signal_handler)
        else:
            signal.signal(signal.SIGINT, signal_handler)

        service_mains = []
        for service_name in args:
            module_path = "chroma_core.services.%s" % service_name

            # Load the module
            mod = __import__(module_path)
            components = module_path.split('.')
            for comp in components[1:]:
                mod = getattr(mod, comp)

            service_label = "%s-%s" % (options['name'], service_name)
            service = getattr(mod, 'Service')()

            service_thread = ServiceMain(service, name = service_label)
            service_thread.start()
            service_mains.append(service_thread)

        while not stopped.is_set():
            # Using a timeout changes the behaviour of CPython's waiting so that it will
            # receive signals (like ctrl-c SIGINT) immediately -- logically we don't want
            # any timeout here, but a pure wait() breaks ctrl-c.
            stopped.wait(10)

        if not options['lightweight_rpc']:
            RpcClientFactory.shutdown_threads()
