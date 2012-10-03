#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from collections import defaultdict
import json
from django.db.models import Q


class LockCache(object):
    instance = None
    enable = True

    def __init__(self):
        from chroma_core.models import Job, StateLock

        self.write_locks = []
        self.write_by_item = defaultdict(list)
        self.read_locks = []
        self.read_by_item = defaultdict(list)
        self.all_by_job = defaultdict(list)
        self.all_by_item = defaultdict(list)

        for job in Job.objects.filter(~Q(state = 'complete')):
            if job.locks_json:
                locks = json.loads(job.locks_json)
                for lock in locks:
                    self._add(StateLock.from_dict(job, lock))

    @classmethod
    def clear(cls):
        cls.instance = None

    @classmethod
    def add(cls, lock):
        cls.getInstance()._add(lock)

    def _add(self, lock):
        if lock.write:
            self.write_locks.append(lock)
            self.write_by_item[lock.locked_item].append(lock)
        else:
            self.read_locks.append(lock)
            self.read_by_item[lock.locked_item].append(lock)

        self.all_by_job[lock.job].append(lock)
        self.all_by_item[lock.locked_item].append(lock)

    @classmethod
    def getInstance(cls):
        if not cls.instance:
            cls.instance = LockCache()
        return cls.instance

    @classmethod
    def get_by_job(cls, job):
        return cls.getInstance().all_by_job[job]

    @classmethod
    def get_all(cls, locked_item):
        return cls.getInstance().all_by_item[locked_item]

    @classmethod
    def get_latest_write(cls, locked_item, not_job = None):
        try:
            if not_job != None:
                return sorted([l for l in cls.getInstance().write_by_item[locked_item] if l.job != not_job], lambda a, b: cmp(a.job.id, b.job.id))[-1]
            else:
                return sorted(cls.getInstance().write_by_item[locked_item], lambda a, b: cmp(a.job.id, b.job.id))[-1]
        except IndexError:
            return None

    @classmethod
    def get_read_locks(cls, locked_item, after, not_job):
        return [x for x in cls.getInstance().read_by_item[locked_item] if after <= x.job.id and x.job != not_job]

    @classmethod
    def get_write(cls, locked_item):
        return cls.getInstance().write_by_item[locked_item]

    @classmethod
    def get_by_locked_item(cls, item):
        return cls.getInstance().all_by_item[item]

    @classmethod
    def get_write_by_locked_item(cls):
        result = {}
        for locked_item, locks in cls.getInstance().write_by_item.items():
            if locks:
                result[locked_item] = sorted(locks, lambda a, b: cmp(a.job.id, b.job.id))[-1]
        return result
