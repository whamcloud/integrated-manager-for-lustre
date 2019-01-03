# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import subprocess
import os
import sys
import logging
import time
import settings

# We use an integer for time and record microseconds.
SECONDSTOMICROSECONDS = 1000000


def all_subclasses(obj):
    """Used to introspect all descendents of a class.  Used because metaclasses
       are a PITA when doing multiple inheritance"""
    sc_recr = []
    for sc_obj in obj.__subclasses__():
        sc_recr.append(sc_obj)
        sc_recr.extend(all_subclasses(sc_obj))
    return sc_recr


def time_str(dt):
    return time.strftime("%Y-%m-%dT%H:%M:%S", dt.timetuple())


def sizeof_fmt(num):
    # http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size/1094933#1094933
    for x in ["bytes", "KB", "MB", "GB", "TB", "EB", "ZB", "YB"]:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0


def sizeof_fmt_detailed(num):
    for x in ["", "kB", "MB", "GB", "TB", "EB", "ZB", "YB"]:
        if num < 1024.0 * 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0

    return int(num)


class timeit(object):
    def __init__(self, logger):
        self.logger = logger

    def __call__(self, method):
        from functools import wraps

        @wraps(method)
        def timed(*args, **kw):
            if self.logger.level <= logging.DEBUG:
                ts = time.time()
                result = method(*args, **kw)
                te = time.time()

                print_args = False
                if print_args:
                    self.logger.debug(
                        "Ran %r (%s, %r) in %2.2fs"
                        % (method.__name__, ", ".join(["%s" % (a,) for a in args]), kw, te - ts)
                    )
                else:
                    self.logger.debug("Ran %r in %2.2fs" % (method.__name__, te - ts))
                return result
            else:
                return method(*args, **kw)

        return timed


class dbperf(object):
    enabled = False
    logger = logging.getLogger("dbperf")

    def __init__(self, label=""):
        # Avoid importing this at module scope in order
        # to co-habit with chroma_settings()
        from django.db import connection

        self.connection = connection

        self.label = label
        self.logger.disabled = not self.enabled
        if self.enabled and not len(self.logger.handlers):
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(logging.FileHandler("dbperf.log"))

    def __enter__(self):
        if settings.DEBUG:
            self.t_initial = time.time()
            self.q_initial = len(self.connection.queries)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.enabled:
            return

        self.t_final = time.time()
        self.q_final = len(self.connection.queries)

        t = self.t_final - self.t_initial
        q = self.q_final - self.q_initial

        if q:
            logfile = open("%s.log" % self.label, "w")
            for query in self.connection.queries[self.q_initial :]:
                logfile.write("(%s) %s\n" % (query["time"], query["sql"]))
            logfile.close()

        if q:
            avg_t = int((t / q) * 1000)
        else:
            avg_t = 0
        self.logger.debug("%s: %d queries in %.2fs (avg %dms)" % (self.label, q, t, avg_t))
        self.q = q


def site_dir():
    def _search_path(path):
        if os.path.exists(os.path.join(path, "settings.py")):
            return path
        else:
            if path == "/":
                raise RuntimeError("Can't find settings.py")
            else:
                return _search_path(os.path.dirname(path))

    return _search_path(os.path.dirname(__file__))


def chroma_settings():
    """
    Walk back up parent directories until settings.py is found.
    Insert that directory as the first entry in sys.path.
    Import the settings module, then return it to the caller.
    """

    sys.path.insert(0, site_dir())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    import settings

    return settings


class CommandError(Exception):
    def __init__(self, cmd, rc, stdout, stderr):
        self.cmd = cmd
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        return """Command failed: %s
    return code %s
    stdout: %s
    stderr: %s""" % (
            self.cmd,
            self.rc,
            self.stdout,
            self.stderr,
        )


class CommandLine(object):
    def try_shell(self, cmdline, mystdout=subprocess.PIPE, mystderr=subprocess.PIPE, stdin_text=None, shell=False):
        rc, out, err = self.shell(cmdline, mystdout, mystderr, stdin_text, shell=shell)

        if rc != 0:
            raise CommandError(cmdline, rc, out, err)
        else:
            return rc, out, err

    def shell(self, cmdline, mystdout=subprocess.PIPE, mystderr=subprocess.PIPE, stdin_text=None, shell=False):
        if stdin_text is not None:
            stdin = subprocess.PIPE
        else:
            stdin = None
        p = subprocess.Popen(cmdline, stdout=mystdout, stderr=mystderr, stdin=stdin, shell=shell)
        if stdin_text is not None:
            p.stdin.write(stdin_text)
        out, err = p.communicate()
        rc = p.wait()
        return rc, out, err


def normalize_nids(nid_list):
    """Cope with the Lustre and users sometimes calling tcp0 'tcp' to allow
       direct comparisons between NIDs"""
    return [normalize_nid(n) for n in nid_list]


def normalize_nid(string):
    """Cope with the Lustre and users sometimes calling tcp0 'tcp' to allow
       direct comparisons between NIDs"""
    if string[-4:] == "@tcp":
        string += "0"

    # remove _ from nids (i.e. @tcp_0 -> @tcp0
    i = string.find("_")
    if i > -1:
        string = string[:i] + string[i + 1 :]

    return string
