#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from collections import defaultdict


class ObjectCache(object):
    instance = None

    def __init__(self):
        from chroma_core.models import ManagedFilesystem, ManagedHost, LNetConfiguration
        from chroma_core.models.target import ManagedTarget, ManagedTargetMount
        objects = defaultdict(list)
        targets = {}
        filter_args = {
            ManagedTargetMount: {"target__not_deleted": True},
            LNetConfiguration: {"host__not_deleted": True}
        }
        for klass in [ManagedTarget, ManagedFilesystem, ManagedHost, ManagedTargetMount, LNetConfiguration]:
            args = filter_args.get(klass, {})
            for object in klass.objects.select_related().filter(**args):
                objects[klass].append(object)
                if hasattr(object, 'content_type'):
                    object = object.downcast()
                    if object.__class__ != klass:
                        objects[object.__class__].append(object)
                        if isinstance(object, ManagedTarget):
                            targets[object.id] = object

        self.targets = targets
        self.objects = objects

    @classmethod
    def get(cls, klass, filter = None):
        return [o for o in cls.getInstance().objects[klass] if not filter or filter(o)]

    @classmethod
    def get_one(cls, klass, filter = None):
        r = [o for o in cls.getInstance().objects[klass] if not filter or filter(o)]
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
        cls.instance = None

    @classmethod
    def host_targets(cls, host_id):
        from chroma_core.models.target import ManagedTargetMount
        mtms = cls.get(ManagedTargetMount, lambda mtm: mtm.host_id == host_id)
        target_ids = set([mtm.target_id for mtm in mtms])
        return [cls.getInstance().targets[i] for i in target_ids]

    @classmethod
    def mtm_targets(cls, mtm_id):
        from chroma_core.models.target import ManagedTargetMount
        mtms = cls.get(ManagedTargetMount, lambda mtm: mtm.id == mtm_id)
        return [cls.getInstance().targets[mtm.target_id] for mtm in mtms]

    @classmethod
    def fs_targets(cls, fs_id):
        from chroma_core.models.target import ManagedMdt, ManagedOst
        return cls.get(ManagedMdt, lambda mdt: mdt.filesystem_id == fs_id) + cls.get(ManagedOst, lambda mdt: mdt.filesystem_id == fs_id)
