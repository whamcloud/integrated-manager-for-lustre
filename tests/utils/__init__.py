import time
import datetime
import contextlib


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
def timed(msg="", threshold=0):
    "Print elapsed time of a block, if over optional threshold."
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        if elapsed >= threshold:
            print(datetime.timedelta(seconds=elapsed), msg)
