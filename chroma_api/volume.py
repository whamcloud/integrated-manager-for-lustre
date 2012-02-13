#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.models import Lun, LunNode

from tastypie.resources import ModelResource
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpBadRequest

from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication

from django.shortcuts import get_object_or_404


class VolumeResource(ModelResource):
    status = fields.CharField()
    kind = fields.CharField()
    volume_nodes = fields.ToManyField("chroma_api.volume_node.VolumeNodeResource", 'lunnode_set', null = True, full = True)

    def dehydrate_kind(self, bundle):
        return bundle.obj.get_kind()

    def dehydrate_status(self, bundle):
        return bundle.obj.ha_status()

    class Meta:
        queryset = Lun.objects.all()
        resource_name = 'volume'
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ['not_deleted']
        ordering = ['label']

    def apply_filters(self, request, filters = None):
        """Override this to build a filesystem filter using Q expressions (not
           possible from build_filters because it only deals with kwargs to filter())"""
        objects = super(VolumeResource, self).apply_filters(request, filters)

        try:
            category = request.GET['category']
            if not category in ['unused', 'usable', None]:
                raise ImmediateHttpResponse(response = HttpBadRequest())
            if category == 'unused':
                objects = Lun.get_unused_luns(objects)
            elif category == 'usable':
                objects = Lun.get_usable_luns(objects)
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

        # Check that we're not trying to modify a Lun that is in
        # used by a target
        try:
            Lun.get_unused_luns().get(id = volume['id'])
        except Lun.DoesNotExist:
            raise AssertionError("Volume %s is in use!")

        lun = get_object_or_404(Lun, id = volume['id'])

        # Apply use,primary values from the request
        for lun_node_params in volume['nodes']:
            primary, use = (lun_node_params['primary'], lun_node_params['use'])

            lun_node = get_object_or_404(LunNode, id = lun_node_params['id'])
            lun_node.primary = primary
            lun_node.use = use
            lun_node.save()

        # Clear use, primary on any nodes not in this request
        from django.db.models import Q
        for lun_node in lun.lunnode_set.filter(~Q(id__in = [n['id'] for n in volume['nodes']])):
            lun_node.primary = False
            lun_node.use = False
            lun_node.save()
