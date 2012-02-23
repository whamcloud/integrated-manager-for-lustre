#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================


from chroma_core.models import ManagedOst, ManagedMdt, ManagedMgs
from chroma_core.models import ManagedFilesystem
from chroma_core.models import Command
import chroma_core.lib.conf_param

import chroma_core.lib.util


import tastypie.http as http
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.utils import custom_response, ConfParamResource, MetricResource, dehydrate_command

from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpBadRequest


class FilesystemResource(MetricResource, ConfParamResource):
    """
    A Lustre filesystem, consisting of one or mode MDTs, and one or more OSTs.

    Note: Lustre filesystems are owned by an MGT, and the ``name`` of a filesystem
    is unique within that MGT.  Do not use ``name`` as a globally unique identifier
    for filesystems in your application.
    """
    bytes_free = fields.IntegerField()
    bytes_total = fields.IntegerField()
    files_free = fields.IntegerField()
    files_total = fields.IntegerField()

    mount_command = fields.CharField(null = True, help_text = "Example command for\
            mounting this filesystem as a Lustre client, e.g. \"mount -t lustre 192.168.0.1:/testfs /mnt/testfs\"")

    osts = fields.ToManyField('chroma_api.target.TargetResource', null = True,
            attribute = lambda bundle: ManagedOst.objects.filter(filesystem = bundle.obj),
            help_text = "List of OSTs which belong to this filesystem")
    # NB a filesystem must always report an MDT, although it may be deleted just before
    # the filesystem is deleted, so use _base_manager
    mdts = fields.ToManyField('chroma_api.target.TargetResource',
            attribute = lambda bundle: ManagedMdt._base_manager.filter(filesystem = bundle.obj), full = True,
            help_text = "List of MDTs in this filesystem, should be at least 1 unless the filesystem\
            is in the process of being deleted")
    mgt = fields.ToOneField('chroma_api.target.TargetResource', attribute = 'mgs', full = True,
            help_text = "The MGT on which this filesystem is registered")

    def _get_stat_simple(self, bundle, stat_name, factor = 1):
        try:
            return bundle.obj.metrics.fetch_last(ManagedMdt, fetch_metrics=[stat_name])[1][stat_name] * 1024
        except (KeyError, IndexError):
            return None

    def dehydrate_mount_command(self, bundle):
        return bundle.obj.mount_command()

    def dehydrate_bytes_free(self, bundle):
        return self._get_stat_simple(bundle, 'kbytesfree', 1024)

    def dehydrate_bytes_total(self, bundle):
        return self._get_stat_simple(bundle, 'kbytestotal', 1024)

    def dehydrate_files_free(self, bundle):
        return self._get_stat_simple(bundle, 'filesfree')

    def dehydrate_files_total(self, bundle):
        return self._get_stat_simple(bundle, 'filestotal')

    class Meta:
        queryset = ManagedFilesystem.objects.all()
        resource_name = 'filesystem'
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ['not_deleted']
        ordering = ['name']
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'delete', 'put']

    def obj_create(self, bundle, request = None, **kwargs):
        try:
            fsname = bundle.data['name']
            mgt_id = bundle.data['mgt_id']
            mgt_lun_id = bundle.data['mgt_lun_id']
            mdt_lun_id = bundle.data['mdt_lun_id']
            ost_lun_ids = bundle.data['ost_lun_ids']
            conf_params = bundle.data['conf_params']
        except KeyError:
            raise ImmediateHttpResponse(HttpBadRequest())

        # mgt_id and mgt_lun_id are mutually exclusive:
        # * mgt_id is a PK of an existing ManagedMgt to use
        # * mgt_lun_id is a PK of a Lun to use for a new ManagedMgt
        assert bool(mgt_id) != bool(mgt_lun_id)

        if not mgt_id:
            mgt = ManagedMgs.create_for_lun(mgt_lun_id, name="MGS")
            mgt_id = mgt.pk
        else:
            mgt_lun_id = ManagedMgs.objects.get(pk = mgt_id).lun.id

        # This is a brute safety measure, to be superceded by
        # some appropriate validation that gives a helpful
        # error to the user.
        all_lun_ids = [mgt_lun_id] + [mdt_lun_id] + ost_lun_ids
        # Test that all values in all_lun_ids are unique
        assert len(set(all_lun_ids)) == len(all_lun_ids)

        from django.db import transaction
        with transaction.commit_on_success():
            mgs = ManagedMgs.objects.get(id=mgt_id)
            fs = ManagedFilesystem(mgs=mgs, name = fsname)
            fs.save()

            for key, value in conf_params:
                chroma_core.lib.conf_param.set_conf_param(fs, key, value)

            ManagedMdt.create_for_lun(mdt_lun_id, filesystem = fs)
            osts = []
            for lun_id in ost_lun_ids:
                osts.append(ManagedOst.create_for_lun(lun_id, filesystem = fs))
        # Important that a commit happens here so that the targets
        # land in DB before the set_state jobs act upon them.

        command = Command.set_state(fs, 'available', "Creating filesystem %s" % fsname)

        filesystem_data = self.full_dehydrate(self.build_bundle(obj = fs)).data

        raise custom_response(self, request, http.HttpAccepted,
                {'command': dehydrate_command(command),
                 'filesystem': filesystem_data})
