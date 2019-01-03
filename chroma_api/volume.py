# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.models import Volume, ManagedFilesystem, HaCluster, ManagedHost

from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpBadRequest

from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.chroma_model_resource import ChromaModelResource
from chroma_api.validation_utils import validate

from django.shortcuts import get_object_or_404
from django.db.models import Q


class WrappedAll(object):
    """Hack to prevent 1 extra query (exact dup) for EVERY volume from executing

    TastyPie will take a callable in as an attribute in a ToManyField.
    During dehydration  ToManyField.dehydrate is called and this is where
    TastyPie grabs the callable and tries to get some objects from it.
    But, in that method, the queryset is forced to a bool, which causes it's
    query to be executed.  Unfortunately, then it is forced to execute again
    to iterate through the list of volumenodes.  It seems the first one
    isn't cached.

    I'm not sure if this is a bug, and if it is one, if it is with TastyPie
    or with Django's ORM.

    This Hacky class is just a workaround.

    This class returns True, but does NOT execute any queries.  This allows
    the hydrate to continue.  Then, when all() is called, it will return
    what it should in that one single select_related query.
    """

    def __call__(self, bundle):
        self.bundle = bundle
        return self

    def all(self):
        return self.bundle.obj.volumenode_set.all().select_related("host")

    def __bool__(self):
        return True

    __nonzero__ = __bool__  # for python 2 and 3 compatibility


class VolumeResource(ChromaModelResource):
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

    status = fields.CharField(
        help_text="A string representing the " "high-availability configuration " "status of the volume."
    )

    kind = fields.CharField(
        help_text="A human readable noun representing "
        "thetype of storage, e.g. 'Linux "
        "partition', 'LVM LV', 'iSCSI LUN'"
    )

    # See notes above about how hacking the attribute saves 1 query / volume
    volume_nodes = fields.ToManyField(
        "chroma_api.volume_node.VolumeNodeResource",
        WrappedAll(),
        null=True,
        full=True,
        help_text="Device nodes which point to this volume",
    )

    storage_resource = fields.ToOneField(
        "chroma_api.storage_resource.StorageResourceResource",
        "storage_resource",
        null=True,
        blank=True,
        full=False,
        help_text="The `storage_resource` corresponding to the " "device which this Volume represents",
    )

    def dehydrate_kind(self, bundle):
        #  Kind comes from the related storage_resource.
        return bundle.obj.get_kind()

    def alter_list_data_to_serialize(self, request, data):
        """Impl to pull out the node's primary and use counts to set status

        Since the query gets this data, it made sense to aggregate it here
        instead of doing another query to do it for each Volume.

        This might only be a marginal speed up.
        """

        for vol_bndl in data["objects"]:
            volumenode_count = len(vol_bndl.data["volume_nodes"])
            primary_count = 0
            failover_count = 0
            for vol_node_bndl in vol_bndl.data["volume_nodes"]:
                primary = vol_node_bndl.data["primary"]
                use = vol_node_bndl.data["use"]
                # True == 1, False = 0
                primary_count += int(primary)
                failover_count += int(not primary and use)
            vol_bndl.data["status"] = Volume.ha_status_label(volumenode_count, primary_count, failover_count)

        return data

    class Meta:
        #  Join in these three models to dehydrate_kind without big penalties
        queryset = (
            Volume.objects.all()
            .select_related(
                "storage_resource",
                "storage_resource__resource_class",
                "storage_resource__resource_class__storage_plugin",
            )
            .prefetch_related("volumenode_set", "volumenode_set__host")
        )
        resource_name = "volume"
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ["not_deleted"]
        ordering = ["label", "size"]
        list_allowed_methods = ["get"]
        detail_allowed_methods = ["get", "put"]
        always_return_data = True

        filtering = {"id": ["exact"], "label": ["exact", "endswith"]}

    def apply_filters(self, request, filters=None):
        objects = super(VolumeResource, self).apply_filters(request, filters)

        try:
            category = request.GET["category"]
            if not category in ["unused", "usable", None]:
                raise ImmediateHttpResponse(response=HttpBadRequest())
            if category == "unused":
                objects = Volume.get_unused_luns(objects)
            elif category == "usable":
                objects = Volume.get_usable_luns(objects)
        except KeyError:
            # Not filtering on category
            pass

        try:
            try:
                objects = objects.filter(
                    Q(volumenode__primary=request.GET["primary"])
                    & Q(volumenode__host__id=request.GET["host_id"])
                    & Q(volumenode__not_deleted=True)
                ).distinct()
            except KeyError:
                # Not filtering on primary, try just host_id
                objects = objects.filter(
                    Q(volumenode__host__id=request.GET["host_id"]) & Q(volumenode__not_deleted=True)
                ).distinct()
        except KeyError:
            # Not filtering on host_id
            pass

        try:
            try:
                fs = ManagedFilesystem.objects.get(pk=request.GET["filesystem_id"])
            except ManagedFilesystem.DoesNotExist:
                objects = objects.filter(id=-1)  # No filesystem so we want to produce an empty list.
            else:
                objects = objects.filter(
                    (Q(managedtarget__managedmdt__filesystem=fs) | Q(managedtarget__managedost__filesystem=fs))
                    | Q(managedtarget__id=fs.mgs.id)
                )
        except KeyError:
            # Not filtering on filesystem_id
            pass

        return objects

    @validate
    def obj_update(self, bundle, **kwargs):
        # FIXME: I'm not exactly sure how cached cached_object_get is -- should
        # we be explicitly getting a fresh one?  I'm just following what the ModelResource
        # obj_update does - jcs
        bundle.obj = self.cached_obj_get(bundle, **self.remove_api_resource_names(kwargs))
        volume = bundle.data

        # Check that we're not trying to modify a Volume that is in
        # used by a target
        try:
            Volume.get_unused_luns(Volume.objects).get(id=volume["id"])
        except Volume.DoesNotExist:
            raise AssertionError("Volume %s is in use!" % volume["id"])

        lun = get_object_or_404(Volume, id=volume["id"])
        node_ids = [node["id"] for node in volume["nodes"]]
        host_ids = set(lun.volumenode_set.filter(id__in=node_ids).values_list("host_id", flat=True))

        # Sanity-check the primary/failover relationships and save if OK
        if not any(host_ids.issubset(host.id for host in cluster.peers) for cluster in HaCluster.all_clusters()):
            error_msg = "Attempt to set primary/secondary VolumeNodes across HA clusters for Volume %s:%s\n" % (
                lun.id,
                lun.label,
            )
            error_msg += "\nVolume Node Hosts %s\n" % ", ".join(
                [str(host) for host in ManagedHost.objects.filter(id__in=host_ids)]
            )
            error_msg += "\nKnown HA Clusters %s\n" % ", ".join(
                ["(%s)" % ", ".join([str(host) for host in cluster.peers]) for cluster in HaCluster.all_clusters()]
            )

            raise ImmediateHttpResponse(response=HttpBadRequest(error_msg))
        # Apply use,primary values from the request
        for node in volume["nodes"]:
            lun.volumenode_set.filter(id=node["id"]).update(primary=node["primary"], use=node["use"])

        # Clear use, primary on any nodes not in this request
        lun.volumenode_set.exclude(id__in=node_ids).update(primary=False, use=False)

        return bundle
