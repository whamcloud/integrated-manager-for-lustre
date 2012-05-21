#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import logging
import time
from django.db import connection


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
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB', 'EB', 'ZB', 'YB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0


def sizeof_fmt_detailed(num):
    for x in ['', 'kB', 'MB', 'GB', 'TB', 'EB', 'ZB', 'YB']:
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
                    self.logger.debug('Ran %r (%s, %r) in %2.2fs' %
                            (method.__name__,
                             ", ".join(["%s" % (a,) for a in args]),
                             kw,
                             te - ts))
                else:
                    self.logger.debug('Ran %r in %2.2fs' %
                            (method.__name__,
                             te - ts))
                return result
            else:
                return method(*args, **kw)

        return timed


class dbperf(object):
    def __init__(self, label = ""):
        self.label = label

    def __enter__(self):
        self.t_initial = time.time()
        self.q_initial = len(connection.queries)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.t_final = time.time()
        self.q_final = len(connection.queries)

        t = self.t_final - self.t_initial
        q = self.q_final - self.q_initial
        print "%s: %d queries in %.2fs (avg %dms)" % (
            self.label, q, t,
            int((t / q) * 1000))
