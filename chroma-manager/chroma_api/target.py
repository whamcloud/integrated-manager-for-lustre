#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
from chroma_core.models.host import Volume, VolumeNode
from chroma_core.models.target import FilesystemMember

import settings
from collections import defaultdict

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from chroma_core.models import ManagedOst, ManagedMdt, ManagedMgs, ManagedTargetMount, ManagedTarget, ManagedFilesystem, Command

import tastypie.http as http
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from tastypie.validation import Validation
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.utils import custom_response, ConfParamResource, MetricResource, dehydrate_command
from chroma_api.fuzzy_lookups import FuzzyLookupFailed, FuzzyLookupException, target_vol_data

# Some lookups for the three 'kind' letter strings used
# by API consumers to refer to our target types
KIND_TO_KLASS = {"MGT": ManagedMgs,
            "OST": ManagedOst,
            "MDT": ManagedMdt}
KLASS_TO_KIND = dict([(v, k) for k, v in KIND_TO_KLASS.items()])
KIND_TO_MODEL_NAME = dict([(k, v.__name__.lower()) for k, v in KIND_TO_KLASS.items()])


class TargetValidation(Validation):
    def is_valid(self, bundle, request=None):
        errors = defaultdict(list)

        if request.method != "POST":
            # TODO: validate PUTs
            return errors

        for mandatory_field in ['kind', 'volume_id']:
            if mandatory_field not in bundle.data or bundle.data[mandatory_field] == None:
                errors[mandatory_field].append("This field is mandatory")

        if errors:
            return errors

        volume_id = bundle.data['volume_id']
        try:
            Volume.objects.get(id = volume_id)
        except Volume.DoesNotExist:
            errors['volume_id'].append("Volume %s not found" % volume_id)

        kind = bundle.data['kind']
        if not kind in KIND_TO_KLASS:
            errors['kind'].append("Invalid target type '%s' (choose from [%s])" % (kind, ",".join(KIND_TO_KLASS.keys())))
        else:
            if issubclass(KIND_TO_KLASS[kind], FilesystemMember):
                if not 'filesystem_id' in bundle.data:
                    errors['filesystem_id'].append("Mandatory for targets of kind '%s'" % kind)
                else:
                    filesystem_id = bundle.data['filesystem_id']
                    try:
                        ManagedFilesystem.objects.get(id = filesystem_id)
                    except ManagedFilesystem.DoesNotExist:
                        errors['filesystem_id'].append("Filesystem %s not found" % filesystem_id)
            if KIND_TO_KLASS[kind] == ManagedMgs:
                mgt_volume = Volume.objects.get(id = volume_id)
                hosts = [vn.host for vn in VolumeNode.objects.filter(volume = mgt_volume, use = True)]
                conflicting_mgs_count = ManagedTarget.objects.filter(~Q(managedmgs = None), managedtargetmount__host__in = hosts).count()
                if conflicting_mgs_count > 0:
                    errors['mgt'].append("Volume %s cannot be used for MGS (only one MGS is allowed per server)" % mgt_volume.label)

                if 'filesystem_id' in bundle.data:
                    bundle.data_errors['filesystem_id'].append("Cannot specify filesystem_id when creating MGT")
            if KIND_TO_KLASS[kind] == ManagedMdt:
                bundle.data_errors['kind'].append("Cannot create MDTs independently of filesystems")

        try:
            errors.update(bundle.data_errors)
        except AttributeError:
            pass

        return errors


class TargetResource(MetricResource, ConfParamResource):
    """
    Lustre targets: MGTs, OSTs and MDTs.

    Typically used for retrieving targets for a particular filesystem (filter on
    filesystem_id) and/or of a particular type (filter on kind).
    """
    filesystems = fields.ListField(null = True, help_text = "For MGTs, the list of filesystems\
            belonging to this MGT.  Null for other targets.")
    filesystem = fields.CharField('chroma_api.filesystem.FilesystemResource', 'filesystem',
        help_text = "For OSTs and MDTs, the owning filesystem.  Null for MGTs.", null = True)
    filesystem_id = fields.IntegerField(help_text = "For OSTs and MDTs, the ``id`` attribute of\
            the owning filesystem.  Null for MGTs.", null = True)
    filesystem_name = fields.CharField(help_text = "For OSTs and MDTs, the ``name`` attribute \
            of the owning filesystem.  Null for MGTs.")

    kind = fields.CharField(help_text = "Type of target, one of %s" % KIND_TO_KLASS.keys())

    volume_name = fields.CharField(attribute = 'volume__label',
            help_text = "The ``label`` attribute of the Volume on which this target exists")

    primary_server = fields.ToOneField('chroma_api.host.HostResource', 'primary_host')
    primary_server_name = fields.CharField(help_text = "Presentation convenience.  Human\
            readable label for the primary server for this target")
    failover_servers = fields.ToManyField('chroma_api.host.HostResource', 'failover_hosts')
    failover_server_name = fields.CharField(help_text = "Presentation convenience.  Human\
            readable label for the secondary server for this target")

    active_host_name = fields.CharField(help_text = "Presentation convenience. Human \
        readable label for the host on which this target is currently started")
    active_host = fields.ToOneField('chroma_api.host.HostResource', 'active_host',
        null = True, help_text = "The server on which this target is currently started, or null if" \
                                 "the target is not currently started")

    def content_type_id_to_kind(self, id):
        if not hasattr(self, 'CONTENT_TYPE_ID_TO_KIND'):
            self.CONTENT_TYPE_ID_TO_KIND = dict([(ContentType.objects.get_for_model(v).id, k) for k, v in KIND_TO_KLASS.items()])

        return self.CONTENT_TYPE_ID_TO_KIND[id]

    class Meta:
        queryset = ManagedTarget.objects.all()
        resource_name = 'target'
        excludes = ['not_deleted', 'bytes_per_inode']
        filtering = {'kind': ['exact'], 'filesystem_id': ['exact'], 'id': ['exact', 'in']}
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        ordering = ['volume_name', 'name']
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'put', 'delete']
        validation = TargetValidation()
        readonly = ['active_host', 'failover_server_name', 'volume_name',
                    'primary_server_name', 'active_host_name', 'filesystems',
                    'name', 'uuid', 'primary_server', 'failover_servers', 'active_host_name']

    def override_urls(self):
        urls = super(TargetResource, self).override_urls()
        from django.conf.urls.defaults import url
        urls.extend([
            url(r"^(?P<resource_name>%s)/(?P<pk>\d+)/resource_graph/$" % self._meta.resource_name, self.wrap_view('get_resource_graph'), name="api_get_resource_graph"),
            #url(r"^(?P<resource_name>%s)/metric/$" % self._meta.resource_name, self.wrap_view('get_metric_list'), name="get_metric_list"),
            #url(r"^(?P<resource_name>%s)/(?P<pk>\d+)/metric/$" % self._meta.resource_name, self.wrap_view('get_metric_detail'), name="get_metric_detail"),
        ])
        return urls

    def dehydrate_filesystems(self, bundle):
        if hasattr(bundle.obj, 'managedmgs'):
            return [{'id': fs.id, 'name': fs.name} for fs in bundle.obj.managedmgs.managedfilesystem_set.all()]
        else:
            return None

    def dehydrate_kind(self, bundle):
        return self.content_type_id_to_kind(bundle.obj.content_type_id)

    def dehydrate_filesystem(self, bundle):
        from chroma_api.filesystem import FilesystemResource
        filesystem = getattr(bundle.obj.downcast(), 'filesystem', None)
        if filesystem:
            return FilesystemResource().get_resource_uri(filesystem)
        else:
            return None

    def dehydrate_filesystem_id(self, bundle):
        return getattr(bundle.obj.downcast(), 'filesystem_id', None)

    def dehydrate_filesystem_name(self, bundle):
        try:
            return bundle.obj.downcast().filesystem.name
        except AttributeError:
            return None

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

    def dehydrate_active_host_uri(self, bundle):
        if bundle.obj.active_mount:
            from chroma_api.host import HostResource
            return HostResource().get_resource_uri(bundle.obj.active_mount.host)
        else:
            return None

    def hydrate_lun_ids(self, bundle):
        if 'lun_ids' in bundle.data:
            return bundle

        try:
            bundle.data['lun_ids'] = []
            for volume_str in bundle.data['volumes']:
                # TODO: Actually use the supplied primary/failover information
                (primary, failover_list, lun_id) = target_vol_data(volume_str)
                bundle.data['lun_ids'].append(lun_id)
        except KeyError:
            bundle.data_errors['volumes'].append("volumes is required if lun_ids is not present")
        except (FuzzyLookupFailed, FuzzyLookupException), e:
            bundle.data_errors['volumes'].append(str(e))

        return bundle

    def hydrate_filesystem_id(self, bundle):
        if 'filesystem_id' in bundle.data:
            return bundle

        try:
            bundle.data['filesystem_id'] = ManagedFilesystem.objects.get(name=bundle.data['filesystem_name']).pk
        except KeyError:
            # Filesystem isn't always required -- could be a MGT
            pass
        except ManagedFilesystem.DoesNotExist:
            bundle.data_errors['filesystem_name'].append("Unknown filesystem: %s" % bundle.data['filesystem_name'])

        return bundle

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
        # Set up an errors dict in the bundle to allow us to carry
        # hydration errors through to validation.
        setattr(bundle, 'data_errors', defaultdict(list))

        # As with the Filesystem resource, full_hydrate() doesn't make sense
        # for our customized Target resource.  As a convention, we'll
        # abstract the logic for mangling the incoming bundle data into
        # hydrate_FIELD methods and call them by hand.
        for field in ['volume_id', 'filesystem_id']:
            method = getattr(self, "hydrate_%s" % field, None)

            if method:
                bundle = method(bundle)

        volume_id = bundle.data['volume_id']
        filesystem_id = bundle.data.get('filesystem_id', None)

        # Should really only be doing one validation pass, but this works
        # OK for now.  It's better than raising a 404 or duplicating the
        # filesystem validation failure if it doesn't exist, anyhow.
        self.is_valid(bundle, request)

        kind = bundle.data['kind']
        if KIND_TO_KLASS[kind] == ManagedOst:
            fs = ManagedFilesystem.objects.get(id=filesystem_id)
            create_kwargs = {'filesystem': fs}
        elif kind == "MGT":
            create_kwargs = {'name': 'MGS'}

        self.is_valid(bundle, request)

        with transaction.commit_on_success():
            target_klass = KIND_TO_KLASS[kind]
            target = target_klass.create_for_volume(volume_id, **create_kwargs)

        command = Command.set_state([(target, 'mounted')], "Creating %s" % kind)
        raise custom_response(self, request, http.HttpAccepted,
                {'command': dehydrate_command(command),
                 'target': self.full_dehydrate(self.build_bundle(obj = target)).data})

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
            lun_node = tm.volume_node
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

        return self.create_response(request, {'graph': graph})
