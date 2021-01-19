# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
This lib provide useful features related to the database.


"""

import os
import traceback

from django.db import transaction, close_old_connections


def exit_if_in_transaction(log):
    if transaction.get_connection().in_atomic_block:
        close_old_connections()

        stack = "".join(traceback.format_stack())

        log.error("Tried to cross a process boundary while in a transaction: {}".format(stack))
        os._exit(-1)
