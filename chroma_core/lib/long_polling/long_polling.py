# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import threading
import time

from django import db

from collections import defaultdict

from chroma_core.lib import util
from chroma_core.services.job_scheduler import lock_cache

# table_name: list events
# When waiting for a table to change a semaphore is added to the list this is trigger when that table changes
events = defaultdict(list)

# timestamps of the change for each table.
# If we don't have a timestamp then default to it changing 1 hour ago.
timestamps = defaultdict(lambda: int(util.SECONDSTOMICROSECONDS * (time.time() - (60 * 60))))

# Semaphore for operations
operation_lock = threading.RLock()


@lock_cache.lock_change_receiver()
def lock_change_receiver(lock, add_remove):
    tables_changed(int(time.time() * util.SECONDSTOMICROSECONDS), [lock.locked_item._meta.db_table])


def tables_changed(timestamp, tables):
    assert type(timestamp) == int

    with operation_lock:
        for table in tables:
            timestamps[table] = max(timestamps[table], timestamp)

            for event in events[table]:
                event.set()


def wait_table_change(table_timestamps, tables_list, timeout):
    with operation_lock:
        last_change_timestamp = int(table_timestamps["max_timestamp"])

        # First see if the table has already changed, we get rounding errors hence the maths.
        for table in tables_list:
            if timestamps[table] > last_change_timestamp:
                return _table_timestamps(tables_list)

        # So now setup the semaphore
        event = threading.Event()

        for table in tables_list:
            events[table].append(event)

    db.connection.close()  # We don't want to hog any connections whilst we are waiting.

    event.wait(timeout)

    with operation_lock:
        for table in tables_list:
            events[table].remove(event)

        if event.isSet():
            return _table_timestamps(tables_list)
        else:
            return 0


def _table_timestamps(tables_list):
    max_timestamp = 0
    table_timestamps = {}

    for table in tables_list:
        table_timestamps[table] = timestamps[table]
        if timestamps[table] > max_timestamp:
            max_timestamp = timestamps[table]

    table_timestamps["max_timestamp"] = max_timestamp

    return table_timestamps
