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
                function_name = 'pg_advisory_lock'
            else:
                function_name = 'pg_try_advisory_lock'

            try:
                lock_id = lock_id._meta.db_table
            except AttributeError:
                pass

            if isinstance(lock_id, str):
                lock_id = binascii.crc32(lock_id.encode('utf-8'))
                if lock_id > 2147483647:
                    lock_id = -(-(lock_id) & 0xffffffff)
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
