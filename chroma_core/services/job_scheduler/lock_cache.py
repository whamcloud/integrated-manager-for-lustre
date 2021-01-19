# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import defaultdict
import json
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType


class LockCache(object):

    # Lock change receivers are called whenever a change occurs to the locks. It allows something to
    # respond to changes. An example would be long polling.
    # The receivers are called with the lock being removed and LOCK_ADD or LOCK_REMOVE as the paramter.
    lock_change_receivers = []
    LOCK_ADD = 1
    LOCK_REMOVE = 2

    def __init__(self):
        from chroma_core.models import Job, StateLock

        self.write_locks = []
        self.write_by_item = defaultdict(list)
        self.read_locks = []
        self.read_by_item = defaultdict(list)
        self.all_by_job = defaultdict(list)
        self.all_by_item = defaultdict(list)

        for job in Job.objects.filter(~Q(state="complete")):
            if job.locks_json:
                locks = json.loads(job.locks_json)
                for lock in locks:
                    self._add(StateLock.from_dict(job, lock))

    def call_receivers(self, lock, add_remove):
        for lock_change_receiver in self.lock_change_receivers:
            lock_change_receiver(lock, add_remove)

    def remove_job(self, job):
        locks = list(self.all_by_job[job.id])
        n = len(locks)
        for lock in locks:
            if lock.write:
                self.write_locks.remove(lock)
                self.write_by_item[lock.locked_item].remove(lock)
            else:
                self.read_locks.remove(lock)
                self.read_by_item[lock.locked_item].remove(lock)
            self.all_by_job[job.id].remove(lock)
            self.all_by_item[lock.locked_item].remove(lock)
            self.call_receivers(lock, self.LOCK_REMOVE)
        return n

    def add(self, lock):
        self._add(lock)

    def _add(self, lock):
        assert lock.job.id is not None

        if lock.write:
            self.write_locks.append(lock)
            self.write_by_item[lock.locked_item].append(lock)
        else:
            self.read_locks.append(lock)
            self.read_by_item[lock.locked_item].append(lock)

        self.all_by_job[lock.job.id].append(lock)
        self.all_by_item[lock.locked_item].append(lock)
        self.call_receivers(lock, self.LOCK_ADD)

    def get_by_job(self, job):
        return self.all_by_job[job.id]

    def get_all(self, locked_item):
        return self.all_by_item[locked_item]

    def get_latest_write(self, locked_item, not_job=None):
        try:
            if not_job is not None:
                return sorted(
                    [l for l in self.write_by_item[locked_item] if l.job != not_job],
                    lambda a, b: cmp(a.job.id, b.job.id),
                )[-1]

            return sorted(self.write_by_item[locked_item], lambda a, b: cmp(a.job.id, b.job.id))[-1]
        except IndexError:
            return None

    def get_read_locks(self, locked_item, after, not_job):
        return [x for x in self.read_by_item[locked_item] if after <= x.job.id and x.job != not_job]

    def get_write(self, locked_item):
        return self.write_by_item[locked_item]

    def get_by_locked_item(self, item):
        return self.all_by_item[item]

    def get_write_by_locked_item(self):
        result = {}
        for locked_item, locks in self.write_by_item.items():
            if locks:
                result[locked_item] = sorted(locks, lambda a, b: cmp(a.job.id, b.job.id))[-1]
        return result


def lock_change_receiver():
    """
    A decorator for connecting receivers to signals that a lock has change.

        @receiver(post_save, sender=MyModel)
        def signal_receiver(sender, **kwargs):
            ...

    """

    def _decorator(func):
        LockCache.lock_change_receivers.append(func)
        return func

    return _decorator


def to_lock_json(lock, add_remove=LockCache.LOCK_ADD):
    if getattr(lock.locked_item, "downcast", None) and callable(lock.locked_item.downcast):
        item = lock.locked_item.downcast()
    else:
        item = lock.locked_item

    return {
        "job_id": lock.job.id,
        "content_type_id": ContentType.objects.get_for_model(item).id,
        "item_id": lock.locked_item.id,
        "uuid": lock.uuid,
        "description": lock.job.description(),
        "lock_type": "write" if lock.write else "read",
        "action": "add" if add_remove == LockCache.LOCK_ADD else "remove",
    }
