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


from collections import defaultdict
from chroma_core.services import log_register
from time import time


log = log_register(__name__)


class ObjectCache(object):
    instance = None

    def __init__(self):
        from chroma_core.models import ManagedFilesystem, ManagedHost, LNetConfiguration
        from chroma_core.models.target import ManagedTarget, ManagedTargetMount
        self.objects = defaultdict(dict)
        filter_args = {
            ManagedTargetMount: {"target__not_deleted": True},
            LNetConfiguration: {"host__not_deleted": True}
        }

        self._cached_models = [ManagedTarget, ManagedFilesystem, ManagedHost, ManagedTargetMount, LNetConfiguration]

        for klass in self._cached_models:
            args = filter_args.get(klass, {})
            for obj in klass.objects.filter(**args):
                self._add(klass, obj)

    def _add(self, klass, instance):
        assert instance.__class__ in self._cached_models

        log.debug("_add %s %s %s" % (instance.__class__, instance.id, id(instance)))

        instance.version = time()
        self.objects[klass][instance.pk] = instance

    @classmethod
    def add(cls, klass, instance):
        cls.getInstance()._add(klass, instance)

    @classmethod
    def get(cls, klass, filter = None):
        assert klass in cls.getInstance()._cached_models
        return [o for o in cls.getInstance().objects[klass].values() if not filter or filter(o)]

    @classmethod
    def get_by_id(cls, klass, instance_id):
        assert klass in cls.getInstance()._cached_models
        try:
            return cls.getInstance().objects[klass][instance_id]
        except KeyError:
            raise klass.DoesNotExist()

    @classmethod
    def get_targets_by_filesystem(cls, filesystem_id):
        return cls.getInstance()._get_targets_by_filesystem(filesystem_id)

    @classmethod
    def fs_targets(cls, fs_id):
        from chroma_core.models import ManagedMgs
        targets = cls.getInstance()._get_targets_by_filesystem(fs_id)
        targets = [t for t in targets if not issubclass(t.downcast_class, ManagedMgs)]
        #log.debug("fs_targets: %s" % targets)
        return targets

    def _get_targets_by_filesystem(self, filesystem_id):
        from chroma_core.models import ManagedTarget, ManagedMdt, ManagedOst, ManagedFilesystem

        # FIXME: This is reasonably efficient but could be improved further by caching the filesystem membership of targets.
        targets = []
        mgs_id = self.objects[ManagedFilesystem][filesystem_id].mgs_id
        targets.append(self.objects[ManagedTarget][mgs_id])

        targets.extend([self.objects[ManagedTarget][mdt['id']] for mdt in ManagedMdt.objects.filter(filesystem = filesystem_id).values('id')])
        targets.extend([self.objects[ManagedTarget][ost['id']] for ost in ManagedOst.objects.filter(filesystem = filesystem_id).values('id')])

        return targets

    @classmethod
    def get_one(cls, klass, filter = None):
        assert klass in cls.getInstance()._cached_models
        r = [o for o in cls.getInstance().objects[klass].values() if not filter or filter(o)]
        if len(r) > 1:
            raise klass.MultipleObjectsReturned
        elif not r:
            raise klass.DoesNotExist
        else:
            return r[0]

    @classmethod
    def target_primary_server(cls, target):
        from chroma_core.models.target import ManagedTargetMount
        primary_mtm = cls.get_one(ManagedTargetMount, lambda mtm: mtm.target.id == target.id and mtm.primary == True)
        return primary_mtm.host

    @classmethod
    def getInstance(cls):
        if not cls.instance:
            cls.instance = ObjectCache()
        return cls.instance

    @classmethod
    def clear(cls):
        log.info('clear')
        cls.instance = None

    @classmethod
    def host_targets(cls, host_id):
        from chroma_core.models.target import ManagedTargetMount, ManagedTarget
        mtms = cls.get(ManagedTargetMount, lambda mtm: mtm.host_id == host_id)

        # FIXME: We have to explicitly restrict to non-deleted targets because ManagedTargetMount
        # instances aren't cleaned up on target deletion.
        target_ids = set([mtm.target_id for mtm in mtms]) & set(cls.getInstance().objects[ManagedTarget].keys())
        return [cls.getInstance().objects[ManagedTarget][i] for i in target_ids]

    @classmethod
    def purge(cls, klass, filter):
        cls.getInstance().objects[klass] = dict([(o.pk, o) for o in cls.getInstance().objects[klass].values() if not filter(o)])

    def _update(self, obj):
        log.debug("update: %s %s" % (obj.__class__, obj.id))
        assert obj.__class__ in self._cached_models
        class_collection = self.objects[obj.__class__]
        if obj.pk in class_collection:
            try:
                fresh_instance = obj.__class__.objects.get(pk = obj.pk)
            except obj.__class__.DoesNotExist:
                return None
            else:
                fresh_instance.version = time()
                class_collection[obj.pk] = fresh_instance
            return fresh_instance

    @classmethod
    def update(cls, obj):
        return cls.getInstance()._update(obj)

    @classmethod
    def mtm_targets(cls, mtm_id):
        from chroma_core.models.target import ManagedTargetMount, ManagedTarget
        mtms = cls.get(ManagedTargetMount, lambda mtm: mtm.id == mtm_id)
        return [cls.getInstance().objects[ManagedTarget][mtm.target_id] for mtm in mtms]
