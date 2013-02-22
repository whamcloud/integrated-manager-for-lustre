#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.models import Volume, VolumeNode, ManagedFilesystem

from tastypie.resources import ModelResource
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpBadRequest

from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication

from django.shortcuts import get_object_or_404
from django.db.models import Q


class VolumeResource(ModelResource):
    """
    A volume represents a unit of storage suitable for use as a Lustre target.  This
    typically corresponds to a SCSI LUN.  Since volumes are frequently accessible from
    multiple hosts via different device nodes, the device node information is represented
    in the volume_node_ resource.  A list of volume nodes is provided
    with each volume in the ``volume_nodes`` list attribute.

    Depending on available volume nodes, the ``status`` attribute may be set to one of:

    :configured-ha: We can build a highly available lustre target on this volume.
    :configured-noha: We can build a Lustre target on this volume but it will
                      only be accessed by a single server so won't be highly
                      available.
    :unconfigured: We do not have enough information to build a Lustre target on
                   this volume.  Either it has no nodes, or none of the nodes is
                   marked for use as the primary server.

    To configure the high availability for a volume before creating a Lustre target,
    you must update the ``use`` and ``primary`` attributes of the volume nodes. To update the
    ``use`` and ``primary`` attributes of a node, use PUT to the volume to access the volume_node
    attribute for the node. Only one node can be identified as primary.

    PUT to a volume with the volume_nodes attribute populated to update the
    ``use`` and ``primary`` attributes of the nodes (i.e. to configure the high
    availability for this volume before creating a Lustre target).  You may
    only identify one node as primary.
    """

    status = fields.CharField(help_text = "A string representing the high-availability \
            configuration status of the volume.")
    kind = fields.CharField(help_text = "A human readable noun representing the \
            type of storage, e.g. 'Linux partition', 'LVM LV', 'iSCSI LUN'")
    volume_nodes = fields.ToManyField("chroma_api.volume_node.VolumeNodeResource",
            lambda bundle: bundle.obj.volumenode_set.filter(host__not_deleted = True),
            null = True, full = True, help_text = "Device nodes which point to this volume")
    storage_resource = fields.ToOneField("chroma_api.storage_resource.StorageResourceResource",
            'storage_resource', null = True, blank = True, full = False, help_text = "The \
            `storage_resource` corresponding to the device which this Volume represents")

    def dehydrate_kind(self, bundle):
        return bundle.obj.get_kind()

    def dehydrate_status(self, bundle):
        return bundle.obj.ha_status()

    class Meta:
        queryset = Volume.objects.all()
        resource_name = 'volume'
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ['not_deleted']
        ordering = ['label', 'size']
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get', 'put']
        always_return_data = True

        filtering = {'id': ['exact'],
                     'label': ['exact', 'endswith']}

    def apply_filters(self, request, filters = None):
        objects = super(VolumeResource, self).apply_filters(request, filters)

        try:
            category = request.GET['category']
            if not category in ['unused', 'usable', None]:
                raise ImmediateHttpResponse(response = HttpBadRequest())
            if category == 'unused':
                objects = Volume.get_unused_luns(objects)
            elif category == 'usable':
                objects = Volume.get_usable_luns(objects)
        except KeyError:
            # Not filtering on category
            pass

        try:
            try:
                objects = objects.filter(Q(volumenode__primary = request.GET['primary']) & Q(volumenode__host__id = request.GET['host_id']))
            except KeyError:
                # Not filtering on primary, try just host_id
                objects = objects.filter(Q(volumenode__host__id = request.GET['host_id']))
        except KeyError:
            # Not filtering on host_id
            pass

        try:
            fs = get_object_or_404(ManagedFilesystem,
                                   pk = request.GET['filesystem_id'])
            objects = objects.filter((Q(managedtarget__managedmdt__filesystem = fs) | Q(managedtarget__managedost__filesystem = fs)) | Q(managedtarget__id = fs.mgs.id))
        except KeyError:
            # Not filtering on filesystem_id
            pass

        return objects

    def obj_update(self, bundle, request, **kwargs):
        # FIXME: I'm not exactly sure how cached cached_object_get is -- should
        # we be explicitly getting a fresh one?  I'm just following what the ModelResource
        # obj_udpate does - jcs
        bundle.obj = self.cached_obj_get(request = request, **self.remove_api_resource_names(kwargs))
        volume = bundle.data

        # Check that we're not trying to modify a Volume that is in
        # used by a target
        try:
            Volume.get_unused_luns().get(id = volume['id'])
        except Volume.DoesNotExist:
            raise AssertionError("Volume %s is in use!")

        lun = get_object_or_404(Volume, id = volume['id'])

        # Apply use,primary values from the request
        for lun_node_params in volume['nodes']:
            primary, use = (lun_node_params['primary'], lun_node_params['use'])

            lun_node = get_object_or_404(VolumeNode, id = lun_node_params['id'])
            lun_node.primary = primary
            lun_node.use = use
            lun_node.save()

        # Clear use, primary on any nodes not in this request
        from django.db.models import Q
        for lun_node in lun.volumenode_set.filter(~Q(id__in = [n['id'] for n in volume['nodes']])):
            lun_node.primary = False
            lun_node.use = False
            lun_node.save()

        return bundle
