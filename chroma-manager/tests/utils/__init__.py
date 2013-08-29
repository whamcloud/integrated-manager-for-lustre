import time
import datetime
import itertools
import contextlib


def wait(timeout=float('inf'), count=None, minwait=0.1, maxwait=1.0):
    "Generate an exponentially backing-off enumeration with optional timeout or count."
    timeout += time.time()
    for index in itertools.islice(itertools.count(), count):
        yield index
        remaining = timeout - time.time()
        if remaining < 0:
            break
        time.sleep(min(minwait, maxwait, remaining))
        minwait *= 2


@contextlib.contextmanager
def patch(obj, **attrs):
    "Monkey patch an object's attributes, restoring them after the block."
    stored = {}
    for name in attrs:
        stored[name] = getattr(obj, name)
        setattr(obj, name, attrs[name])
    try:
        yield
    finally:
        for name in stored:
            setattr(obj, name, stored[name])


@contextlib.contextmanager
def timed(msg='', threshold=0):
    "Print elapsed time of a block, if over optional threshold."
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        if elapsed >= threshold:
            print datetime.timedelta(seconds=elapsed), msg
