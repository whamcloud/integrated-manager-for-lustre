# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
This lib provide useful features related to the database.

Advisory_lock is a decorator that provide a way to block the execution of
a function and to hold execution of possible locking decorated function.
This decorator is thread and process safe since it relies on an external
feature built-in postgresql.
  @advisory_lock(lock, wait)
    - lock: this is an identifier which could be a string, a number or a
            model class
    - wait: a boolean. If False, it obtains the lock and continues execution
            making subsequent waiting locks to wait until lock is released.
            If True, it blocks the execution until the lock is released.

"""


from functools import wraps
from contextlib import contextmanager
import binascii


def advisory_lock(lock, wait=True):
    def use_advisory_lock(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            lock_id = lock

            from django.db import DEFAULT_DB_ALIAS, connections

            if wait:
                function_name = "pg_advisory_lock"
            else:
                function_name = "pg_try_advisory_lock"

            try:
                lock_id = lock_id._meta.db_table
            except AttributeError:
                pass

            if isinstance(lock_id, str):
                lock_id = binascii.crc32(lock_id.encode("utf-8"))
                if lock_id > 2147483647:
                    lock_id = -(-(lock_id) & 0xFFFFFFFF)
            elif not isinstance(lock_id, (int, long)):
                raise ValueError("DB Lock identifier must be a string, a model or an integer")

            @contextmanager
            def acquiring_lock():

                lock_query = "select %s(%d)" % (function_name, lock_id)
                cursor = connections[DEFAULT_DB_ALIAS].cursor()
                cursor.execute(lock_query)
                acquired = cursor.fetchone()[0]

                try:
                    yield acquired
                finally:
                    release_query = "select pg_advisory_unlock (%d)" % lock_id
                    cursor.execute(release_query)

            with acquiring_lock():
                result = func(*args, **kwargs)

            return result

        return wrapper

    return use_advisory_lock
