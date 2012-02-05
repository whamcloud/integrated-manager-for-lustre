#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.models import Lun, LunNode, ManagedTargetMount

from requesthandler import RequestHandler
from chroma_api.requesthandler import APIResponse

from django.shortcuts import get_object_or_404


class Handler(RequestHandler):
    def get(self, request, id = None, category = None):
        if id:
            lun = get_object_or_404(Lun, id = id)
            return lun.to_dict()
        else:
            if not category in ['unused', 'usable', None]:
                return APIResponse(None, 400)

            if category == 'unused':
                luns = Lun.get_unused_luns()
            elif category == 'usable':
                luns = Lun.get_usable_luns()
            elif category == None:
                luns = Lun.objects.all()

            return [lun.to_dict() for lun in luns]

    def put(self, request, id = None):
        if id:
            # Single resource -- single dict, 'volumes' is a list of one
            volume = request.data
            volume['id'] = id
            volumes = [volume]
        else:
            # Multiple resource -- list of volumes
            volumes = request.data

        def assert_lunnode_unused(lun_node):
            try:
                tm = lun_node.managedtargetmount_set.get()
                raise AssertionError("Volume %s, Node %s is in use by target %s" % (lun.id, lun_node.id, tm.target))
            except ManagedTargetMount.DoesNotExist:
                pass

        for volume in volumes:
            # Apply use,primary values from the request
            for lun_node_params in volume['nodes']:
                primary, use = (lun_node_params['primary'], lun_node_params['use'])

                lun_node = get_object_or_404(LunNode, id = lun_node_params['id'])
                assert_lunnode_unused(lun_node)
                lun_node.primary = primary
                lun_node.use = use
                lun_node.save()

            # Clear use,primary on any nodes not in this request
            from django.db.models import Q
            lun = get_object_or_404(Lun, id = volume['id'])
            for lun_node in lun.lunnode_set.filter(~Q(id__in = [n['id'] for n in volume['nodes']])):
                assert_lunnode_unused(lun_node)
                lun_node.primary = False
                lun_node.use = False
                lun_node.save()
