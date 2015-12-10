#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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


import threading
import time

from collections import defaultdict

from chroma_core.lib import util


# table_name: list events
# When waiting for a table to change a semaphore is added to the list this is trigger when that table changes
events = defaultdict(list)

# timestamps of the change for each table.
# If we don't have a timestamp then default to it changing 1 hour ago.
timestamps = defaultdict(lambda: int(util.SECONDSTOMICROSECONDS * (time.time() - (60 * 60))))

# Semaphore for operations
operation_lock = threading.RLock()


def table_change(timestamp, table):
    assert type(timestamp) == int

    with operation_lock:
        timestamps[table] = timestamp

        for event in events[table]:
            event.set()


def wait_table_change(table_timestamps, tables_list, timeout):
    with operation_lock:
        last_change_timestamp = int(table_timestamps['max_timestamp'])

        # First see if the table has already changed, we get rounding errors hence the maths.
        for table in tables_list:
            if timestamps[table] > last_change_timestamp:
                return _table_timestamps(tables_list)

        # So now setup the semaphore
        event = threading.Event()

        for table in tables_list:
            events[table].append(event)

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

    table_timestamps['max_timestamp'] = max_timestamp

    return table_timestamps
