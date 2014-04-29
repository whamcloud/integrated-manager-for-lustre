#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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


from collections import defaultdict
import json
from django.db.models import Q


class LockCache(object):
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

    def remove_job(self, job):
        locks = list(self.all_by_job[job.id])
        n = len(locks)
        for l in locks:
            if l.write:
                self.write_locks.remove(l)
                self.write_by_item[l.locked_item].remove(l)
            else:
                self.read_locks.remove(l)
                self.read_by_item[l.locked_item].remove(l)
            self.all_by_job[job.id].remove(l)
            self.all_by_item[l.locked_item].remove(l)

        return n

    def add(self, lock):
        self._add(lock)

    def _add(self, lock):
        if lock.write:
            self.write_locks.append(lock)
            self.write_by_item[lock.locked_item].append(lock)
        else:
            self.read_locks.append(lock)
            self.read_by_item[lock.locked_item].append(lock)

        if lock.job.id is None:
            raise RuntimeError()

        self.all_by_job[lock.job.id].append(lock)
        self.all_by_item[lock.locked_item].append(lock)

    def get_by_job(self, job):
        return self.all_by_job[job.id]

    def get_all(self, locked_item):
        return self.all_by_item[locked_item]

    def get_latest_write(self, locked_item, not_job = None):
        try:
            if not_job != None:
                return sorted([l for l in self.write_by_item[locked_item] if l.job != not_job], lambda a, b: cmp(a.job.id, b.job.id))[-1]
            else:
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
