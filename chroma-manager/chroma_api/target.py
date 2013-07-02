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


from chroma_core.models.host import Volume, VolumeNode
from chroma_core.models.target import FilesystemMember, NotAFileSystemMember
import chroma_core.lib.conf_param
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

import settings
from collections import defaultdict

from django.shortcuts import get_object_or_404, Http404
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from chroma_core.models import ManagedOst, ManagedMdt, ManagedMgs, ManagedTarget, ManagedFilesystem

import tastypie.http as http
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from tastypie.utils import dict_strip_unicode_keys
from tastypie.validation import Validation
from tastypie.resources import BadRequest, ImmediateHttpResponse
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.utils import custom_response, ConfParamResource, MetricResource, dehydrate_command

# Some lookups for the three 'kind' letter strings used
# by API consumers to refer to our target types
KIND_TO_KLASS = {"MGT": ManagedMgs,
            "OST": ManagedOst,
            "MDT": ManagedMdt}
KLASS_TO_KIND = dict([(v, k) for k, v in KIND_TO_KLASS.items()])
KIND_TO_MODEL_NAME = dict([(k, v.__name__.lower()) for k, v in KIND_TO_KLASS.items()])


class TargetValidation(Validation):
    def _validate_post(self, bundle, request):
        errors = defaultdict(list)

        for mandatory_field in ['kind', 'volume_id']:
            if mandatory_field not in bundle.data or bundle.data[mandatory_field] == None:
                errors[mandatory_field].append("This field is mandatory")

        if errors:
            return errors

        volume_id = bundle.data['volume_id']
        try:
            volume = Volume.objects.get(id = volume_id)
        except Volume.DoesNotExist:
            errors['volume_id'].append("Volume %s not found" % volume_id)
        else:
            if ManagedTarget.objects.filter(volume = volume).count():
                errors['volume_id'].append("Volume %s in use" % volume_id)

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
                        filesystem = ManagedFilesystem.objects.get(id = filesystem_id)
                    except ManagedFilesystem.DoesNotExist:
                        errors['filesystem_id'].append("Filesystem %s not found" % filesystem_id)
                    else:
                        if filesystem.immutable_state:
                            errors['filesystem_id'].append("Filesystem %s is unmanaged" % filesystem.name)

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

            if 'conf_params' in bundle.data:
                conf_param_errors = chroma_core.lib.conf_param.validate_conf_params(KIND_TO_KLASS[kind], bundle.data['conf_params'])
                if conf_param_errors:
                    errors['conf_params'] = conf_param_errors

        try:
            errors.update(bundle.data_errors)
        except AttributeError:
            pass

        return errors

    def _validate_put(self, bundle, request):
        errors = defaultdict(list)
        if 'conf_params' in bundle.data and bundle.data['conf_params'] is not None:
            try:
                target_klass = KIND_TO_KLASS[bundle.data['kind']]
            except KeyError:
                errors['kind'].append('Must be one of %s' % KIND_TO_KLASS.keys())
            else:
                try:
                    target = target_klass.objects.get(pk = bundle.data['id'])
                except KeyError:
                    errors['id'].append('Field is mandatory')
                except target_klass.DoesNotExist:
                    errors['id'].append('No %s with ID %s found' % (target_klass.__name__, bundle.data['id']))
                else:

                    if target.immutable_state:
                        # Check that the conf params are unmodified
                        existing_conf_params = chroma_core.lib.conf_param.get_conf_params(target)
                        if not chroma_core.lib.conf_param.compare(existing_conf_params, bundle.data['conf_params']):
                            errors['conf_params'].append("Cannot modify conf_params on immutable_state objects")
                    else:
                        conf_param_errors = chroma_core.lib.conf_param.validate_conf_params(target_klass, bundle.data['conf_params'])
                        if conf_param_errors:
                            errors['conf_params'] = conf_param_errors
        return errors

    def is_valid(self, bundle, request=None):
        if request.method == "POST":
            return self._validate_post(bundle, request)
        elif request.method == "PUT":
            return self._validate_put(bundle, request)
        else:
            return {}


class TargetResource(MetricResource, ConfParamResource):
    """
    A Lustre target.

    Typically used for retrieving targets for a particular file system (by filtering on
    ``filesystem_id``) and/or of a particular type (by filtering on ``kind``).

    A Lustre target may be a management target (MGT), a metadata target (MDT), or an
    object store target (OST).

    A single target may be created using POST, and many targets may be created using
    PATCH, with a request body as follows:

    ::

        {
          objects: [...one or more target objects...],
          deletions: []
        }

    """
    filesystems = fields.ListField(null = True, help_text = "For MGTs, the list of file systems\
            belonging to this MGT.  Null for other targets.")
    filesystem = fields.CharField('chroma_api.filesystem.FilesystemResource', 'filesystem',
        help_text = "For OSTs and MDTs, the owning file system.  Null for MGTs.", null = True)
    filesystem_id = fields.IntegerField(help_text = "For OSTs and MDTs, the ``id`` attribute of\
            the owning file system.  Null for MGTs.", null = True)
    filesystem_name = fields.CharField(help_text = "For OSTs and MDTs, the ``name`` attribute \
            of the owning file system.  Null for MGTs.")

    kind = fields.CharField(help_text = "Type of target, one of %s" % KIND_TO_KLASS.keys())

    volume_name = fields.CharField(attribute = 'volume__label',
            help_text = "The ``label`` attribute of the volume on which this target exists")

    primary_server = fields.ToOneField('chroma_api.host.HostResource', 'primary_host', full=False)
    primary_server_name = fields.CharField(help_text = "Human\
            readable label for the primary server for this target")
    failover_servers = fields.ListField(null=True)
    failover_server_name = fields.CharField(help_text = "Human\
            readable label for the secondary server for this target")

    active_host_name = fields.CharField(help_text = "Human \
        readable label for the host on which this target is currently started")
    active_host = fields.ToOneField('chroma_api.host.HostResource', 'active_host',
        null = True, help_text = "The server on which this target is currently started, or null if "
                                 "the target is not currently started")

    volume = fields.ToOneField('chroma_api.volume.VolumeResource', 'full_volume', full = True, help_text = "\
                             The volume on which this target is stored.")

    def content_type_id_to_kind(self, id):
        if not hasattr(self, 'CONTENT_TYPE_ID_TO_KIND'):
            self.CONTENT_TYPE_ID_TO_KIND = dict([(ContentType.objects.get_for_model(v).id, k) for k, v in KIND_TO_KLASS.items()])

        return self.CONTENT_TYPE_ID_TO_KIND[id]

    def full_dehydrate(self, bundle):
        """The first call in the dehydrate cycle.

        The ui, calls this directly, in addition to calling through the
        normal api path.  So, use it to initialize the fs cache.
        """

        self._init_cached_fs()

        return super(TargetResource, self).full_dehydrate(bundle)

    class Meta:
        # ManagedTarget is a Polymorphic Model which gets related
        # to content_type in the __metaclass__
        queryset = ManagedTarget.objects.select_related(
            'content_type', 'volume',
            'volume__storage_resource__resource_class',
            'volume__storage_resource__resource_class__storage_plugin',
            'managedost', 'managedmdt', 'managedmgs').prefetch_related(
            'managedtargetmount_set', 'managedtargetmount_set__host',
            'managedtargetmount_set__host__lnetconfiguration')
        resource_name = 'target'
        excludes = ['not_deleted', 'bytes_per_inode', 'reformat']
        filtering = {'kind': ['exact'], 'filesystem_id': ['exact'], 'host_id': ['exact'], 'id': ['exact', 'in'], 'immutable_state': ['exact'], 'name': ['exact']}
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        ordering = ['volume_name', 'name']
        list_allowed_methods = ['get', 'post', 'patch']
        detail_allowed_methods = ['get', 'put', 'delete']
        validation = TargetValidation()
        always_return_data = True
        readonly = ['active_host', 'failover_server_name', 'volume_name',
                    'primary_server_name', 'active_host_name', 'filesystems',
                    'name', 'uuid', 'primary_server', 'failover_servers',
                    'active_host_name', 'ha_label', 'filesystem_name',
                    'filesystem_id']

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
        #  Limit this to one db hit per mgs, caching might help
        mgs = bundle.obj.downcast()
        if type(mgs) == ManagedMgs:
            return [{'id': fs.id, 'name': fs.name} for fs in
                    bundle.obj.managedmgs.managedfilesystem_set.all()]
        else:
            return None

    def dehydrate_kind(self, bundle):
        return self.content_type_id_to_kind(bundle.obj.content_type_id)

    def dehydrate_filesystem_id(self, bundle):

        #  The ID is free - no db hit
        return getattr(bundle.obj.downcast(), 'filesystem_id', None)

    def _init_cached_fs(self):

        # Object to hold seen filesystems, to preventing multiple
        # db hits for the same filesystem.
        self._fs_cache = defaultdict(ManagedFilesystem)

    def _get_cached_fs(self, bundle):
        """Cache the ManagedFilesystem as they are seen.

        The ManageFile can be accessed many times.  Use this method to get
        it and the number of DB hits is reduced.

        """

        #  Only OST and MDT are FS members.  Those subclass are joined in above
        #  So this lookup is free accept for intial ManageFilesystem lookup
        ost_or_mdt = bundle.obj.downcast()
        if (type(ost_or_mdt) == ManagedOst or
            type(ost_or_mdt) == ManagedMdt):
            val = getattr(ost_or_mdt, 'filesystem_id', None)
            if val not in self._fs_cache:
                #  Only DB hit in this method.
                self._fs_cache[val] = ost_or_mdt.filesystem

            return self._fs_cache[val]  # a ManagedFilesystem
        else:
            raise NotAFileSystemMember(type(ost_or_mdt))

    def dehydrate_filesystem(self, bundle):
        """Get the URL to load a ManagedFileSystem"""

        try:
            from chroma_api.filesystem import FilesystemResource

            filesystem = self._get_cached_fs(bundle)
            return FilesystemResource().get_resource_uri(filesystem)
        except NotAFileSystemMember:
            return None

    def dehydrate_filesystem_name(self, bundle):

        try:
            filesystem = self._get_cached_fs(bundle)
            return filesystem.name
        except NotAFileSystemMember:
            return None

    def dehydrate_primary_server_name(self, bundle):
        return bundle.obj.primary_host.get_label()

    def dehydrate_failover_servers(self, bundle):
        return bundle.obj.failover_hosts

    def dehydrate_failover_server_name(self, bundle):
        try:
            return bundle.obj.failover_hosts[0].get_label()
        except IndexError:
            return "---"

    def dehydrate_active_host_name(self, bundle):
        if bundle.obj.active_mount:
            return bundle.obj.active_mount.host.get_label()
        else:
            return "---"

    def dehydrate_active_host_uri(self, bundle):
        if bundle.obj.active_mount:
            from chroma_api.host import HostResource
            return HostResource().get_resource_uri(bundle.obj.active_mount.host)
        else:
            return None

    def build_filters(self, filters = None):
        """Override this to convert a 'kind' argument into a DB field which exists"""
        custom_filters = {}
        for key, val in filters.items():
            if key == 'kind':
                del filters[key]
                try:
                    custom_filters['content_type__model'] = KIND_TO_MODEL_NAME[val.upper()]
                except KeyError:
                    # Don't want to just pass this because it will
                    # potentially remove all filters and make this a list
                    # operation.
                    custom_filters['content_type__model'] = None
            elif key == 'host_id':
                del filters[key]
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
        except Http404 as exc:
            raise custom_response(self, request, http.HttpNotFound, {'filesystem': exc})
        except KeyError:
            # Not filtering on filesystem_id
            pass

        try:
            try:
                objects = objects.filter(Q(managedtargetmount__primary = request.GET['primary']) & Q(managedtargetmount__host__id = request.GET['host_id']))
            except KeyError:
                # Not filtering on primary, try just host_id
                objects = objects.filter(Q(managedtargetmount__host__id = request.GET['host_id']))
        except KeyError:
            # Not filtering on host_id
            pass

        return objects

    def patch_list(self, request, **kwargs):
        """
        Specialization of patch_list to do bulk target creation in a single RPC to job_scheduler (and
        consequently in a single command).
        """
        deserialized = self.deserialize(request, request.raw_post_data, format=request.META.get('CONTENT_TYPE', 'application/json'))

        if "objects" not in deserialized:
            raise BadRequest("Invalid data sent.")

        if len(deserialized["objects"]) and 'put' not in self._meta.detail_allowed_methods:
            raise ImmediateHttpResponse(response=http.HttpMethodNotAllowed())

        # If any of the included targets is not a creation, then
        # skip to a normal PATCH instead of this special case one
        for target_data in deserialized['objects']:
            if 'id' in target_data or 'resource_uri' in target_data:
                super(TargetResource, self).patch_list(request, **kwargs)

        # Validate and prepare each target dict for consumption by job_scheduler
        for target_data in deserialized['objects']:
            data = self.alter_deserialized_detail_data(request, target_data)
            bundle = self.build_bundle(data=dict_strip_unicode_keys(data))
            self.is_valid(bundle, request)

            target_data['content_type'] = ContentType.objects.get_for_model(KIND_TO_KLASS[target_data['kind']]).natural_key()

        targets, command = JobSchedulerClient.create_targets(deserialized['objects'])

        raise custom_response(self, request, http.HttpAccepted,
                              {'command': dehydrate_command(command),
                               'targets': [self.get_resource_uri(target) for target in targets]})

    def obj_create(self, bundle, request = None, **kwargs):
        # Set up an errors dict in the bundle to allow us to carry
        # hydration errors through to validation.
        setattr(bundle, 'data_errors', defaultdict(list))

        bundle.data['content_type'] = ContentType.objects.get_for_model(KIND_TO_KLASS[bundle.data['kind']]).natural_key()

        # Should really only be doing one validation pass, but this works
        # OK for now.  It's better than raising a 404 or duplicating the
        # filesystem validation failure if it doesn't exist, anyhow.
        self.is_valid(bundle, request)

        targets, command = JobSchedulerClient.create_targets([bundle.data])

        if request.method == 'POST':
            raise custom_response(self, request, http.HttpAccepted,
                                  {'command': dehydrate_command(command),
                                   'target': self.full_dehydrate(self.build_bundle(obj=targets[0])).data})

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
