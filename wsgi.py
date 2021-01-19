# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import os
import sys
import multiprocessing

USE_CONSOLE = "USE_CONSOLE" in os.environ
PROFILE = "PROFILE" in os.environ

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))


# Credit: https://medium.com/@maxmaxmaxmax/measuring-performance-of-python-based-apps-using-gunicorn-and-cprofile-ee4027b2be41
if PROFILE:
    import cProfile
    import pstats
    import StringIO
    import logging
    import time

    PROFILE_LIMIT = int(os.environ.get("PROFILE_LIMIT", 30))
    PROFILER = bool(int(os.environ.get("PROFILER", 1)))

    print(
        """
    # ** USAGE:
    $ PROFILE_LIMIT=100 gunicorn -c ./wsgi_profiler_conf.py wsgi
    # ** TIME MEASUREMENTS ONLY:
    $ PROFILER=0 gunicorn -c ./wsgi_profiler_conf.py wsgi
    """
    )

    def profiler_enable(worker, req):
        worker.profile = cProfile.Profile()
        worker.profile.enable()
        worker.log.info("PROFILING %d: %s" % (worker.pid, req.uri))

    def profiler_summary(worker, req):
        s = StringIO.StringIO()
        worker.profile.disable()
        ps = pstats.Stats(worker.profile, stream=s).sort_stats("time", "cumulative")
        ps.print_stats(PROFILE_LIMIT)

        logging.error("\n[%d] [INFO] [%s] URI %s" % (worker.pid, req.method, req.uri))
        logging.error("[%d] [INFO] %s" % (worker.pid, unicode(s.getvalue())))

    def pre_request(worker, req):
        worker.start_time = time.time()
        if PROFILER is True:
            profiler_enable(worker, req)

    def post_request(worker, req, *args):
        total_time = time.time() - worker.start_time
        logging.error("\n[%d] [INFO] [%s] Load Time: %.3fs\n" % (worker.pid, req.method, total_time))
        if PROFILER is True:
            profiler_summary(worker, req)


# From Gunicorn Docs:
# DO NOT scale the number of workers to the
# number of clients you expect to have.
# Gunicorn should only need 4-12 worker processes to handle
# hundreds or thousands of requests per second.
#
# Obviously, your particular hardware and application are
# going to affect the optimal number of workers.
# Our recommendation is to start with the above guess and tune using
# TTIN and TTOU signals while the application is under load.
# Always remember, there is such a thing as too many workers.
# After a point your worker processes will start thrashing system resources
# decreasing the throughput of the entire system.
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)


# Get the derived settings for gunicorn.
# We import inside this function
# to not pollute the module.
def get_derived_settings():
    import settings

    bind = "{}:{}".format(settings.PROXY_HOST, settings.HTTP_API_PORT)

    pidfile = settings.GUNICORN_PID_PATH

    errorlog = "-" if USE_CONSOLE else os.path.join(settings.LOG_PATH, "gunicorn-error.log")
    accesslog = None

    timeout = settings.LONG_POLL_TIMEOUT_SECONDS + 10

    return (bind, pidfile, errorlog, accesslog, timeout)


# Get the WSGI app that
# will run in gunicorn.
# We import inside this function
# to not pollute the module.
def get_app():
    import django.db
    import threading

    django.db.connections._connections = threading.local()

    from django.core.wsgi import get_wsgi_application

    return get_wsgi_application()


def when_ready(server):
    try:
        from systemd.daemon import notify

        notify("READY=1")
    except ImportError:
        pass


def post_fork(server, worker):
    from chroma_core.services.log import log_set_filename, log_enable_stdout

    if USE_CONSOLE:
        log_enable_stdout()
    else:
        log_set_filename("http.log")


application = get_app()
worker_class = "gevent"
bind, pidfile, errorlog, accesslog, timeout = get_derived_settings()
