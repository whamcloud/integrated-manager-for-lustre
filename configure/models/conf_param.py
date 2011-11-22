
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models
from configure.lib.job import DependOn
from polymorphic.models import DowncastMetaclass

from configure.models.jobs import Job
from configure.models.target import ManagedMgs, ManagedMdt, ManagedOst
from configure.models.filesystem import ManagedFilesystem


class ApplyConfParams(Job):
    mgs = models.ForeignKey(ManagedMgs)

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Update conf_params on %s" % (self.mgs.primary_server())

    def get_steps(self):
        from configure.models import ConfParam
        from configure.lib.job import job_log
        new_params = ConfParam.objects.filter(version__gt = self.mgs.conf_param_version_applied).order_by('version')
        steps = []

        new_param_count = new_params.count()
        if new_param_count > 0:
            job_log.info("ApplyConfParams %d, applying %d new conf_params" % (self.id, new_param_count))
            # If we have some new params, create N ConfParamSteps and one ConfParamVersionStep
            from configure.lib.job import ConfParamStep, ConfParamVersionStep
            highest_version = 0
            for param in new_params:
                steps.append((ConfParamStep, {"conf_param_id": param.id}))
                highest_version = max(highest_version, param.version)
            steps.append((ConfParamVersionStep, {"mgs_id": self.mgs.id, "version": highest_version}))
        else:
            # If we have no new params, no-op
            job_log.warning("ApplyConfParams %d, mgs %d has no params newer than %d" % (self.id, self.mgs.id, self.mgs.conf_param_version_applied))
            from configure.lib.job import NullStep
            steps.append((NullStep, {}))

        return steps

    def get_deps(self):
        return DependOn(self.mgs.downcast(), 'mounted')


class ConfParam(models.Model):
    __metaclass__ = DowncastMetaclass
    mgs = models.ForeignKey(ManagedMgs)
    key = models.CharField(max_length = 512)
    # A None value means "lctl conf_param -d", i.e. clear the setting
    value = models.CharField(max_length = 512, blank = True, null = True)
    version = models.IntegerField()

    class Meta:
        app_label = 'configure'

    @staticmethod
    def get_latest_params(queryset):
        # Assumption: conf params don't experience high flux, so it's not
        # obscenely inefficient to pull all historical values out of the DB before picking
        # the latest ones.
        from collections import defaultdict
        by_key = defaultdict(list)
        for conf_param in queryset:
            by_key[conf_param.get_key()].append(conf_param)

        result_list = []
        for key, conf_param_list in by_key.items():
            conf_param_list.sort(lambda a, b: cmp(b.version, a.version))
            result_list.append(conf_param_list[0])

        return result_list

    def get_key(self):
        """Subclasses to return the fully qualified key, e.g. a FilesystemConfParam
           prepends the filesystem name to self.key"""
        return self.key


class FilesystemClientConfParam(ConfParam):
    filesystem = models.ForeignKey(ManagedFilesystem)

    class Meta:
        app_label = 'configure'

    def __init__(self, *args, **kwargs):
        super(FilesystemClientConfParam, self).__init__(*args, **kwargs)
        self.mgs = self.filesystem.mgs.downcast()

    def get_key(self):
        return "%s.%s" % (self.filesystem.name, self.key)


class FilesystemGlobalConfParam(ConfParam):
    filesystem = models.ForeignKey(ManagedFilesystem)

    def __init__(self, *args, **kwargs):
        super(FilesystemGlobalConfParam, self).__init__(*args, **kwargs)
        self.mgs = self.filesystem.mgs.downcast()

    def get_key(self):
        return "%s.%s" % (self.filesystem.name, self.key)

    class Meta:
        app_label = 'configure'


class MdtConfParam(ConfParam):
    # TODO: allow setting MDT to None to allow setting the param for
    # all MDT on an MGS (and set this param for MDT in RegisterTargetJob)
    mdt = models.ForeignKey(ManagedMdt)

    def __init__(self, *args, **kwargs):
        super(MdtConfParam, self).__init__(*args, **kwargs)
        self.mgs = self.mdt.filesystem.mgs.downcast()

    def get_key(self):
        return "%s.%s" % (self.mdt.name, self.key)

    class Meta:
        app_label = 'configure'


class OstConfParam(ConfParam):
    # TODO: allow setting OST to None to allow setting the param for
    # all OSTs on an MGS (and set this param for OSTs in RegisterTargetJob)
    ost = models.ForeignKey(ManagedOst)

    def __init__(self, *args, **kwargs):
        super(OstConfParam, self).__init__(*args, **kwargs)
        self.mgs = self.ost.filesystem.mgs.downcast()

    def get_key(self):
        return "%s.%s" % (self.ost.name, self.key)

    class Meta:
        app_label = 'configure'
