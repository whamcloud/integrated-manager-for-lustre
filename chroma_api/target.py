#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import settings

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from chroma_core.models import ManagedOst, ManagedMdt, ManagedMgs, ManagedTargetMount, ManagedTarget, ManagedFilesystem, Command
from chroma_core.lib.state_manager import StateManager

import tastypie.http as http
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.utils import custom_response, ConfParamResource, dehydrate_command

# Some lookups for the three 'kind' letter strings used
# by API consumers to refer to our target types
KIND_TO_KLASS = {"MGT": ManagedMgs,
            "OST": ManagedOst,
            "MDT": ManagedMdt}
KLASS_TO_KIND = dict([(v, k) for k, v in KIND_TO_KLASS.items()])
KIND_TO_MODEL_NAME = dict([(k, v.__name__.lower()) for k, v in KIND_TO_KLASS.items()])


class TargetResource(ConfParamResource):
    filesystems = fields.ListField()
    filesystem_id = fields.IntegerField()
    filesystem_name = fields.CharField()
    kind = fields.CharField()

    lun_name = fields.CharField(attribute = 'lun__label')
    primary_server_name = fields.CharField()
    failover_server_name = fields.CharField()
    active_host_name = fields.CharField()

    def content_type_id_to_kind(self, id):
        if not hasattr(self, 'CONTENT_TYPE_ID_TO_KIND'):
            self.CONTENT_TYPE_ID_TO_KIND = dict([(ContentType.objects.get_for_model(v).id, k) for k, v in KIND_TO_KLASS.items()])

        return self.CONTENT_TYPE_ID_TO_KIND[id]

    class Meta:
        queryset = ManagedTarget.objects.all()
        resource_name = 'target'
        excludes = ['not_deleted']
        filtering = {'kind': ['exact'], 'filesystem_id': ['exact']}
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        ordering = ['lun_name']

    def override_urls(self):
        from django.conf.urls.defaults import url
        return [
            url(r"^(?P<resource_name>%s)/(?P<pk>\d+)/resource_graph/$" % self._meta.resource_name, self.wrap_view('get_resource_graph'), name="api_get_resource_graph"),
        ]

    def dehydrate_filesystems(self, bundle):
        if hasattr(bundle.obj, 'managedmgs'):
            return [{'id': fs.id, 'name': fs.name} for fs in bundle.obj.managedmgs.managedfilesystem_set.all()]
        else:
            return None

    def dehydrate_kind(self, bundle):
        return self.content_type_id_to_kind(bundle.obj.content_type_id)

    def dehydrate_filesystem_id(self, bundle):
        return getattr(bundle.obj, 'filesystem_id', None)

    def dehydrate_filesystem_name(self, bundle):
        try:
            return bundle.obj.filesystem.name
        except AttributeError:
            return None

    #def dehydrate_lun_name(self, bundle):
    #    return bundle.obj.lun.label

    def dehydrate_primary_server_name(self, bundle):
        return bundle.obj.primary_server().pretty_name()

    def dehydrate_failover_server_name(self, bundle):
        try:
            return bundle.obj.managedtargetmount_set.get(primary = False).host.pretty_name()
        except ManagedTargetMount.DoesNotExist:
            return "---"

    def dehydrate_active_host_name(self, bundle):
        if bundle.obj.active_mount:
            return bundle.obj.active_mount.host.pretty_name()
        else:
            return "---"

    def build_filters(self, filters = None):
        """Override this to convert a 'kind' argument into a DB field which exists"""
        custom_filters = {}
        for key, val in filters.items():
            if key == 'kind':
                del filters[key]
                custom_filters['content_type__model'] = KIND_TO_MODEL_NAME[val]
            elif key == 'host_id':
                del filters[key]
                custom_filters['managedtargetmount__host__id'] = val
            elif key == 'filesystem_id':
                # Remove filesystem_id as we
                # do a custom query generation for it in apply_filters
                del filters[key]

        filters = super(TargetResource, self).build_filters(filters)
        filters.update(custom_filters)
        return filters

    def apply_filters(self, request, filters = None):
        """Override this to build a filesystem filter using Q expressions (not
           possible from build_filters because it only deals with kwargs to filter())"""
        objects = super(TargetResource, self).apply_filters(request, filters)
        try:
            fs = get_object_or_404(ManagedFilesystem, pk = request.GET['filesystem_id'])
            objects = objects.filter((Q(managedmdt__filesystem = fs) | Q(managedost__filesystem = fs)) | Q(id = fs.mgs.id))
        except KeyError:
            # Not filtering on filesystem_id
            pass

        return objects

    def obj_create(self, bundle, request = None, **kwargs):
        kind = bundle.data['kind']
        if not kind in KIND_TO_KLASS:
            raise custom_response(self, request, http.HttpBadRequest, {})

        lun_ids = bundle.data['lun_ids']
        filesystem_id = bundle.data.get('filesystem_id', None)

        # TODO: move validation into a proper tastypie Validation() object (thereby
        # get proper response instead of 500s
        if KIND_TO_KLASS[kind] == ManagedMgs and filesystem_id:
            raise ValueError("Cannot specify filesystem_id creating MGTs")
        elif KIND_TO_KLASS[kind] == ManagedMdt:
            raise ValueError("Cannot create MDTs independently of filesystems")
        elif len(lun_ids) < 1:
            raise ValueError("Require at least one LUN to create a target")

        if KIND_TO_KLASS[kind] == ManagedOst:
            fs = ManagedFilesystem.objects.get(id=filesystem_id)
            create_kwargs = {'filesystem': fs}
        elif kind == "MGT":
            create_kwargs = {'name': 'MGS'}

        targets = []
        with transaction.commit_on_success():
            for lun_id in lun_ids:
                target_klass = KIND_TO_KLASS[kind]
                target = target_klass.create_for_lun(lun_id, **create_kwargs)
                targets.append(target)

        message = "Creating %s" % kind
        if len(lun_ids) > 1:
            message += "s"

        with transaction.commit_on_success():
            command = Command(message = "Creating %s%s" % (kind, "s" if len(lun_ids) > 1 else ""))
            command.save()
        for target in targets:
            StateManager.set_state(target, 'mounted', command.pk)
        raise custom_response(self, request, http.HttpAccepted, dehydrate_command(command))

    def get_resource_graph(self, request, **kwargs):
        target = self.cached_obj_get(request=request, **self.remove_api_resource_names(kwargs))

        from chroma_core.models import AlertState

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

        return self.create_response(request, {
            'storage_alerts': [a.to_dict() for a in storage_alerts],
            'lustre_alerts': [a.to_dict() for a in lustre_alerts],
            'graph': graph})
