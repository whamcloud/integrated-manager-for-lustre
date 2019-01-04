# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import time
import threading
import sys
from threading import Thread
from collections import defaultdict

from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction

from chroma_core.lib import util
from chroma_core.services.log import log_register

is_job_scheduler = "job_scheduler" in sys.argv

log = log_register(__name__.split(".")[-1])


# Semaphore for operations
operation_lock = threading.RLock()


class DatabaseChangedThread(Thread):
    def __init__(self, timestamp, tablenames):
        super(DatabaseChangedThread, self).__init__()
        self.timestamp = timestamp
        self.tablenames = tablenames

        log.debug("Starting DatabaseChangedThead for %s time %s" % (self.tablenames, self.timestamp))

    def run(self):
        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

        JobSchedulerClient.tables_changed(self.timestamp, self.tablenames)


def _propagate_table_change(table_names):
    timestamp = int(time.time() * util.SECONDSTOMICROSECONDS)

    if is_job_scheduler:
        import long_polling

        long_polling.tables_changed(timestamp, table_names)
    else:
        DatabaseChangedThread(timestamp, table_names).start()


_pending_table_changes = defaultdict(set)


def _transaction_commit_rollback(using, commit, original_commit_fn, original_rollback_fn):
    with operation_lock:

        transaction.connections[using].commit = original_commit_fn
        transaction.connections[using].rollback = original_rollback_fn

        if commit:
            log.debug("Flushing pending changes for %s" % using)
            transaction.connections[using].commit()
            _propagate_table_change(list(_pending_table_changes[using]))
        else:
            log.debug("Rollback pending changes for %s" % using)
            transaction.connections[using].rollback()

        del _pending_table_changes[using]


@receiver(post_save)
@receiver(post_delete)
def database_changed(sender, **kwargs):
    table_name = sender._meta.db_table

    if table_name.startswith("chroma_core"):  # We are only interested in our tables, not the django ones.
        using = kwargs.pop("using", DEFAULT_DB_ALIAS)

        if transaction.is_managed(using) is False:  # Not a managed transaction so the change has occurred
            log.debug("Propagating tablechange for %s" % table_name)
            _propagate_table_change([table_name])
        else:  # This is a transaction and until it commits it has not happened
            with operation_lock:
                if using not in _pending_table_changes:
                    log.debug("New transaction change %s using %s" % (table_name, using))

                    original_commit_fn = transaction.connections[using].commit
                    original_rollback_fn = transaction.connections[using].rollback

                    transaction.connections[using].commit = lambda: _transaction_commit_rollback(
                        using, True, original_commit_fn, original_rollback_fn
                    )

                    transaction.connections[using].rollback = lambda: _transaction_commit_rollback(
                        using, False, original_commit_fn, original_rollback_fn
                    )

                log.debug("Adding pending change %s using %s" % (table_name, using))
                _pending_table_changes[using].add(table_name)
