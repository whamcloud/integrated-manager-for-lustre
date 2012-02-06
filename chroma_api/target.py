#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import settings

from django.shortcuts import get_object_or_404
from django.db import transaction

from chroma_core.models import ManagedOst, ManagedMdt, ManagedMgs, ManagedTargetMount, ManagedTarget, ManagedFilesystem, Command
from chroma_core.models import Lun, LunNode
from chroma_api.requesthandler import AnonymousRESTRequestHandler, APIResponse
from chroma_core.lib.state_manager import StateManager
import chroma_core.lib.conf_param


KIND_TO_KLASS = {"MGT": ManagedMgs,
            "OST": ManagedOst,
            "MDT": ManagedMdt}
KLASS_TO_KIND = dict([(v, k) for k, v in KIND_TO_KLASS.items()])


def create_target(lun_id, target_klass, **kwargs):
    target = target_klass(**kwargs)
    target.save()

    def create_target_mount(lun_node):
        mount = ManagedTargetMount(
            block_device = lun_node,
            target = target,
            host = lun_node.host,
            mount_point = target.default_mount_path(lun_node.host),
            primary = lun_node.primary)
        mount.save()

    lun = Lun.objects.get(pk = lun_id)
    try:
        primary_lun_node = lun.lunnode_set.get(primary = True)
        create_target_mount(primary_lun_node)
    except LunNode.DoesNotExist:
        raise RuntimeError("No primary lun_node exists for lun %s, cannot created target" % lun)
    except LunNode.MultipleObjectsReturned:
        raise RuntimeError("Multiple primary lun_nodes exist for lun %s, internal error")

    for secondary_lun_node in lun.lunnode_set.filter(use = True, primary = False):
        create_target_mount(secondary_lun_node)

    return target


class TargetHandler(AnonymousRESTRequestHandler):
    def put(self, request, id):
        target = get_object_or_404(ManagedTarget, pk = id).downcast()
        try:
            conf_params = request.data['conf_params']
        except KeyError:
            return APIResponse(None, 400)

        # TODO: validate the parameters before trying to set any of them

        for k, v in conf_params.items():
            chroma_core.lib.conf_param.set_conf_param(target, k, v)

    def post(self, request, kind, filesystem_id = None, lun_ids = []):
        if not kind in KIND_TO_KLASS:
            return APIResponse(None, 400)

        # TODO: define convention for API errors, and put some
        # helpful messages in here
        # Cannot specify a filesystem to which an MGT should belong
        if kind == "MGT" and filesystem_id:
            return APIResponse(None, 400)

        # Cannot create MDTs with this call (it is done in filesystem creation)
        if kind == "MDT":
            return APIResponse(None, 400)

        # Need at least one LUN
        if len(lun_ids) < 1:
            return APIResponse(None, 400)

        if kind == "OST":
            fs = ManagedFilesystem.objects.get(id=filesystem_id)
            create_kwargs = {'filesystem': fs}
        elif kind == "MGT":
            create_kwargs = {'name': 'MGS'}

        targets = []
        with transaction.commit_on_success():
            for lun_id in lun_ids:
                targets.append(create_target(lun_id, KIND_TO_KLASS[kind], **create_kwargs))

        message = "Creating %s" % kind
        if len(lun_ids) > 1:
            message += "s"

        with transaction.commit_on_success():
            command = Command(message = "Creating OSTs")
            command.save()
        for target in targets:
            StateManager.set_state(target, 'mounted', command.pk)
        return APIResponse(command.to_dict(), 202)

    def get(self, request, id = None, host_id = None, filesystem_id = None, kind = None):
        if id:
            target = get_object_or_404(ManagedTarget, pk = id).downcast()
            return target.to_dict()
        else:
            targets = []

            # Apply kind filter
            if kind:
                klasses = [KIND_TO_KLASS[kind]]
            else:
                klasses = [ManagedMgs, ManagedMdt, ManagedOst]

            for klass in klasses:
                filter_kwargs = {}
                if klass == ManagedMgs and filesystem_id:
                    # For MGT, filesystem_id filters on the filesystem belonging to the MGT
                    filter_kwargs['managedfilesystem__id'] = filesystem_id
                elif klass != ManagedMgs and filesystem_id:
                    # For non-MGT, filesystem_id filters on the target belonging to the filesystem
                    filter_kwargs['filesystem__id'] = filesystem_id

                for t in klass.objects.filter(**filter_kwargs):
                    # Apply host filter
                    # FIXME: this filter should be done with a query instead of in a loop
                    if host_id and ManagedTargetMount.objects.filter(target = t, host__id = host_id).count() == 0:
                        continue
                    else:
                        d = t.to_dict()
                        d['available_transitions'] = StateManager.available_transitions(t)
                        targets.append(d)
            return targets


class TargetResourceGraphHandler(AnonymousRESTRequestHandler):
    def get(self, request, id):
        from chroma_core.models import AlertState
        from chroma_core.models import ManagedTarget
        from django.shortcuts import get_object_or_404
        target = get_object_or_404(ManagedTarget, pk = id).downcast()

        ancestor_records = set()
        parent_records = set()
        storage_alerts = set()
        lustre_alerts = set(AlertState.filter_by_item(target))
        from collections import defaultdict
        rows = defaultdict(list)
        id_edges = []
        for tm in target.managedtargetmount_set.all():
            lustre_alerts |= set(AlertState.filter_by_item(tm))
            lun_node = tm.block_device
            if lun_node.storage_resource:
                parent_record = lun_node.storage_resource
                from chroma_core.lib.storage_plugin.query import ResourceQuery

                parent_records.add(parent_record)

                storage_alerts |= ResourceQuery().record_all_alerts(parent_record)
                ancestor_records |= set(ResourceQuery().record_all_ancestors(parent_record))

                def row_iterate(parent_record, i):
                    if not parent_record in rows[i]:
                        rows[i].append(parent_record)
                    for p in parent_record.parents.all():
                        #if 25 in [parent_record.id, p.id]:
                        #    id_edges.append((parent_record.id, p.id))
                        id_edges.append((parent_record.id, p.id))
                        row_iterate(p, i + 1)
                row_iterate(parent_record, 0)

        for i in range(0, len(rows) - 1):
            this_row = rows[i]
            next_row = rows[i + 1]

            def nextrow_affinity(obj):
                # if this has a link to anything in the next row, what
                # index in the next row?
                for j in range(0, len(next_row)):
                    notional_edge = (obj.id, next_row[j].id)
                    if notional_edge in id_edges:
                        return j
                return None

            this_row.sort(lambda a, b: cmp(nextrow_affinity(a), nextrow_affinity(b)))

        box_width = 120
        box_height = 80
        xborder = 40
        yborder = 40
        xpad = 20
        ypad = 20

        height = 0
        width = len(rows) * box_width + (len(rows) - 1) * xpad
        for i, items in rows.items():
            total_height = len(items) * box_height + (len(items) - 1) * ypad
            height = max(total_height, height)

        height = height + yborder * 2
        width = width + xborder * 2

        edges = [e for e in id_edges]
        nodes = []
        x = 0
        for i, items in rows.items():
            total_height = len(items) * box_height + (len(items) - 1) * ypad
            y = (height - total_height) / 2
            for record in items:
                resource = record.to_resource()
                alert_count = len(ResourceQuery().resource_get_alerts(resource))
                if alert_count != 0:
                    highlight = "#ff0000"
                else:
                    highlight = "#000000"
                nodes.append({
                    'left': x,
                    'top': y,
                    'title': record.alias_or_name(),
                    'icon': "%simages/storage_plugin/%s.png" % (settings.STATIC_URL, resource.icon),
                    'type': resource.get_class_label(),
                    'id': record.id,
                    'highlight': highlight
                    })
                y += box_height + ypad
            x += box_width + xpad

        graph = {
                'edges': edges,
                'nodes': nodes,
                'item_width': box_width,
                'item_height': box_height,
                'width': width,
                'height': height
                }

        return {
            'storage_alerts': [a.to_dict() for a in storage_alerts],
            'lustre_alerts': [a.to_dict() for a in lustre_alerts],
            'graph': graph}
