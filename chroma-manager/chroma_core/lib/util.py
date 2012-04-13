#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


def all_subclasses(obj):
    """Used to introspect all descendents of a class.  Used because metaclasses
       are a PITA when doing multiple inheritance"""
    sc_recr = []
    for sc_obj in obj.__subclasses__():
        sc_recr.append(sc_obj)
        for sc in all_subclasses(sc_obj):
            sc_recr.append(sc)
    return sc_recr


def time_str(dt):
    import time
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
            import time
            import logging
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
