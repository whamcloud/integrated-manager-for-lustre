# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import defaultdict
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

from django.db.models import Q
from chroma_core.models import ManagedFilesystem, ManagedTarget
from chroma_core.models import ManagedOst, ManagedMdt, ManagedMgs
from chroma_core.models import Volume, VolumeNode
from chroma_core.models import Command
from chroma_core.models.filesystem import HSM_CONTROL_KEY, HSM_CONTROL_PARAMS

import tastypie.http as http
from tastypie import fields
from tastypie.validation import Validation
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.utils import custom_response, ConfParamResource, MetricResource, dehydrate_command
from chroma_api.validation_utils import validate
from chroma_core.lib import conf_param


class FilesystemValidation(Validation):
    def _validate_put(self, bundle, request):
        errors = defaultdict(list)

        if "conf_params" in bundle.data and bundle.data["conf_params"] is not None:
            try:
                fs = ManagedFilesystem.objects.get(pk=bundle.data["id"])
            except ManagedFilesystem.DoesNotExist:
                errors["id"] = "Filesystem with id %s not found" % bundle.data["id"]
            except KeyError:
                errors["id"] = "Field is mandatory"
            else:
                if fs.immutable_state:
                    if not conf_param.compare(bundle.data["conf_params"], conf_param.get_conf_params(fs)):
                        errors["conf_params"].append("Cannot modify conf_params on immutable_state objects")
                else:
                    conf_param_errors = conf_param.validate_conf_params(ManagedFilesystem, bundle.data["conf_params"])
                    if conf_param_errors:
                        errors["conf_params"] = conf_param_errors

        return errors

    def _validate_post(self, bundle, request):
        errors = defaultdict(list)

        targets = defaultdict(list)

        # Check 'mgt', 'mdts', 'osts' are present and compose
        # a record of targets which will be formatted
        try:
            # Check that client hasn't specified an existing MGT
            # *and* a volume to format.
            if "id" in bundle.data["mgt"] and "volume_id" in bundle.data["mgt"]:
                errors["mgt"].append("id and volume_id are mutually exclusive")

            mgt = bundle.data["mgt"]
            if "volume_id" in mgt:
                targets["mgt"].append(mgt)
        except KeyError:
            errors["mgt"].append("This field is mandatory")
        try:
            targets["mdts"].extend(bundle.data["mdts"])
        except KeyError:
            errors["mdts"].append("This field is mandatory")
        try:
            targets["osts"].extend(bundle.data["osts"])
        except KeyError:
            errors["osts"].append("This field is mandatory")

        if "conf_params" not in bundle.data:
            errors["conf_params"].append("This field is mandatory")

        if "name" not in bundle.data:
            errors["name"].append("This field is mandatory")

        # Return if some of the things we're going to validate in detail are absent
        if len(errors):
            return errors

        # As all fields are present we can be more specific about the errors.
        errors["mgt"] = defaultdict(list)
        errors["mdts"] = defaultdict(list)
        errors["osts"] = defaultdict(list)

        # Validate filesystem name
        if len(bundle.data["name"]) > 8:
            errors["name"].append("Name '%s' too long (max 8 characters)" % bundle.data["name"])
        if len(bundle.data["name"]) < 1:
            errors["name"].append("Name '%s' too short (min 1 character)" % bundle.data["name"])
        if bundle.data["name"].find(" ") != -1:
            errors["name"].append("Name may not contain spaces")

        # Check volume IDs are present and correct
        used_volume_ids = set()

        def check_volume(field, volume_id):
            # Check we haven't tried to use the same volume twice
            if volume_id in used_volume_ids:
                return "Volume ID %s specified for multiple targets!" % volume_id

            try:
                # Check the volume exists
                volume = Volume.objects.get(id=volume_id)
                try:
                    # Check the volume isn't in use
                    target = ManagedTarget.objects.get(volume=volume)
                    return "Volume with ID %s is already in use by target %s" % (volume_id, target)
                except ManagedTarget.DoesNotExist:
                    pass
            except Volume.DoesNotExist:
                return "Volume with ID %s not found" % volume_id

            used_volume_ids.add(volume_id)

        try:
            mgt_volume_id = bundle.data["mgt"]["volume_id"]
            error = check_volume("mgt", mgt_volume_id)
            if error:
                errors["mgt"]["volume_id"].append(error)
        except KeyError:
            mgt_volume_id = None

            try:
                mgt = ManagedMgs.objects.get(id=bundle.data["mgt"]["id"])
                if mgt.immutable_state:
                    errors["mgt"]["id"].append("MGT is unmanaged")

                try:
                    ManagedFilesystem.objects.get(name=bundle.data["name"], mgs=mgt)
                    errors["mgt"]["name"].append(
                        "A file system with name '%s' already exists for this MGT" % bundle.data["name"]
                    )
                except ManagedFilesystem.DoesNotExist:
                    pass
            except KeyError:
                errors["mgt"]["id"].append("One of id or volume_id must be set")
        except ManagedMgs.DoesNotExist:
            errors["mgt"]["id"].append("MGT with ID %s not found" % (bundle.data["mgt"]["id"]))

        for mdt in bundle.data["mdts"]:
            try:
                mdt_volume_id = mdt["volume_id"]
                check_volume("mdts", mdt_volume_id)
            except KeyError:
                errors["mdts"]["volume_id"].append("volume_id attribute is mandatory for mdt " % mdt["id"])

        for ost in bundle.data["osts"]:
            try:
                volume_id = ost["volume_id"]
                check_volume("osts", volume_id)
            except KeyError:
                errors["osts"]["volume_id"].append("volume_id attribute is mandatory for ost " % ost["id"])

        # If formatting an MGS, check its not on a host already used as an MGS
        # If this is an MGS, there may not be another MGS on
        # this host
        if mgt_volume_id:
            mgt_volume = Volume.objects.get(id=mgt_volume_id)
            hosts = [vn.host for vn in VolumeNode.objects.filter(volume=mgt_volume, use=True)]
            conflicting_mgs_count = ManagedTarget.objects.filter(
                ~Q(managedmgs=None), managedtargetmount__host__in=hosts
            ).count()
            if conflicting_mgs_count > 0:
                errors["mgt"]["volume_id"].append(
                    "Volume %s cannot be used for MGS (only one MGS is allowed per server)" % mgt_volume.label
                )

        def validate_target(klass, target):
            target_errors = defaultdict(list)

            volume = Volume.objects.get(id=target["volume_id"])
            if "inode_count" in target and "bytes_per_inode" in target:
                target_errors["inode_count"].append("inode_count and bytes_per_inode are mutually exclusive")

            if "conf_params" in target:
                conf_param_errors = conf_param.validate_conf_params(klass, target["conf_params"])
                if conf_param_errors:
                    # FIXME: not really representing target-specific validations cleanly,
                    # will sort out while fixing HYD-1077.
                    target_errors["conf_params"] = conf_param_errors

            for setting in ["inode_count", "inode_size", "bytes_per_inode"]:
                if setting in target:
                    if target[setting] is not None and not isinstance(target[setting], int):
                        target_errors[setting].append("Must be an integer")

            # If they specify and inode size and a bytes_per_inode, check the inode fits
            # within the ratio
            try:
                inode_size = target["inode_size"]
                bytes_per_inode = target["bytes_per_inode"]
                if inode_size >= bytes_per_inode:
                    target_errors["inode_size"].append("inode_size must be less than bytes_per_inode")
            except KeyError:
                pass

            # If they specify an inode count, check it will fit on the device
            try:
                inode_count = target["inode_count"]
            except KeyError:
                # If no inode_count is specified, no need to check it against inode_size
                pass
            else:
                try:
                    inode_size = target["inode_size"]
                except KeyError:
                    inode_size = {ManagedMgs: 128, ManagedMdt: 512, ManagedOst: 256}[klass]

                if inode_size is not None and inode_count is not None:
                    if inode_count * inode_size > volume.size:
                        target_errors["inode_count"].append(
                            "%d %d-byte inodes too large for %s-byte device" % (inode_count, inode_size, volume.size)
                        )

            return target_errors

        # Validate generic target settings
        for attr, targets in targets.items():
            for target in targets:
                klass = ManagedTarget.managed_target_of_type(
                    attr[0:3]
                )  # We get osts, mdts, mgs so just take the first 3 letters.

                target_errors = validate_target(klass, target)

                if target_errors:
                    errors[attr].update(target_errors)

        conf_param_errors = conf_param.validate_conf_params(ManagedFilesystem, bundle.data["conf_params"])
        if conf_param_errors:
            errors["conf_params"] = conf_param_errors

        def recursive_count(o):
            """Count the number of non-empty dicts/lists or other objects"""
            if isinstance(o, dict):
                c = 0
                for v in o.values():
                    c += recursive_count(v)
                return c
            elif isinstance(o, list):
                c = 0
                for v in o:
                    c += recursive_count(v)
                return c
            else:
                return 1

        if not recursive_count(errors):
            errors = {}

        return errors

    def is_valid(self, bundle, request=None):
        if request.method == "POST":
            return self._validate_post(bundle, request)
        elif request.method == "PUT":
            return self._validate_put(bundle, request)
        else:
            return {}


class FilesystemResource(MetricResource, ConfParamResource):
    """
    A Lustre file system, associated with exactly one MGT and consisting of
    one or mode MDTs and one or more OSTs.

    When using POST to create a file system, specify volumes to use like this:
    ::

        {osts: [{volume_id: 22}],
        mdt: {volume_id: 23},
        mgt: {volume_id: 24}}

    To create a file system using an existing MGT instead of creating a new
    MGT, set the `id` attribute instead of the `volume_id` attribute for
    that target (i.e. `mgt: {id: 123}`).

    Note: A Lustre file system is owned by an MGT, and the ``name`` of the file system
    is unique within that MGT.  Do not use ``name`` as a globally unique identifier
    for a file system in your application.
    """

    bytes_free = fields.IntegerField()
    bytes_total = fields.IntegerField()
    files_free = fields.IntegerField()
    files_total = fields.IntegerField()
    client_count = fields.IntegerField(help_text="Number of Lustre clients which are connected to this file system")

    mount_command = fields.CharField(
        null=True,
        help_text='Example command for\
            mounting this file system on a Lustre client, e.g. "mount -t lustre 192.168.0.1:/testfs /mnt/testfs"',
    )

    mount_path = fields.CharField(
        null=True,
        help_text='Path for mounting the file system\
            on a Lustre client, e.g. "192.168.0.1:/testfs"',
    )

    osts = fields.ToManyField(
        "chroma_api.target.TargetResource",
        null=True,
        attribute=lambda bundle: ManagedOst.objects.filter(filesystem=bundle.obj),
        help_text="List of OSTs which belong to this file system",
    )
    mdts = fields.ToManyField(
        "chroma_api.target.TargetResource",
        null=True,
        full=True,
        attribute=lambda bundle: ManagedMdt.objects.filter(filesystem=bundle.obj),
        help_text="List of MDTs in this file system, should be at least 1 unless the "
        "file system is in the process of being deleted",
    )
    mgt = fields.ToOneField(
        "chroma_api.target.TargetResource",
        attribute="mgs",
        full=True,
        help_text="The MGT on which this file system is registered",
    )

    def _get_stat_simple(self, bundle, klass, stat_name, factor=1.0):
        try:
            return bundle.obj.metrics.fetch_last(klass, fetch_metrics=[stat_name])[1][stat_name] * factor
        except (KeyError, IndexError, TypeError):
            return None

    def dehydrate_mount_path(self, bundle):
        return bundle.obj.mount_path()

    def dehydrate_mount_command(self, bundle):
        path = self.dehydrate_mount_path(bundle)
        if path:
            return "mount -t lustre %s /mnt/%s" % (path, bundle.obj.name)
        else:
            return None

    def dehydrate_bytes_free(self, bundle):
        return self._get_stat_simple(bundle, ManagedOst, "kbytesfree", 1024)

    def dehydrate_bytes_total(self, bundle):
        return self._get_stat_simple(bundle, ManagedOst, "kbytestotal", 1024)

    def dehydrate_files_free(self, bundle):
        return self._get_stat_simple(bundle, ManagedMdt, "filesfree")

    def dehydrate_files_total(self, bundle):
        return self._get_stat_simple(bundle, ManagedMdt, "filestotal")

    def get_hsm_control_params(self, mdt, bundle):
        all_params = set(HSM_CONTROL_PARAMS.keys())
        available_params = all_params - set([bundle.data["cdt_status"]])
        bundle_params = []

        # Strip the mdt down for brevity of transport and also to
        # avoid problems with the PUT.
        (resource, id) = mdt.data["resource_uri"].split("/")[-3:-1]
        safe_mdt = dict(kind=mdt.data["kind"], resource=resource, id=id, conf_params=mdt.data["conf_params"])

        for param in available_params:
            bundle_params.append(
                dict(
                    mdt=safe_mdt,
                    param_key=HSM_CONTROL_KEY,
                    param_value=param,
                    verb=HSM_CONTROL_PARAMS[param]["verb"],
                    long_description=HSM_CONTROL_PARAMS[param]["long_description"],
                )
            )

        return bundle_params

    def dehydrate(self, bundle):
        # Have to do this here because we can't guarantee ordering during
        # full_dehydrate to ensure that the mdt bundles are available.
        try:
            mdt = next(m for m in bundle.data["mdts"] if "mdt.hsm_control" in m.data["conf_params"])
            bundle.data["cdt_status"] = mdt.data["conf_params"]["mdt.hsm_control"]
            bundle.data["cdt_mdt"] = mdt.data["resource_uri"]
            bundle.data["hsm_control_params"] = self.get_hsm_control_params(mdt, bundle)
        except StopIteration:
            pass

        # Now the number of MDT's is known calculate the client count. The client count is calculated by the number of connections
        # divided by the number of MDT's. In the case, that is possible durring creation and deletion of filesystems, where the mdt
        # count is 0 then the connected clients must be zero.
        if len(bundle.data["mdts"]) == 0:
            bundle.data["client_count"] = 0
        else:
            bundle.data["client_count"] = self._get_stat_simple(
                bundle, ManagedMdt, "client_count", factor=1.0 / len(bundle.data["mdts"])
            )

        return bundle

    class Meta:
        queryset = ManagedFilesystem.objects.all()
        resource_name = "filesystem"
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ["not_deleted", "ost_next_index", "mdt_next_index"]
        ordering = ["name"]
        filtering = {"id": ["exact", "in"], "name": ["exact"]}
        list_allowed_methods = ["get", "post"]
        detail_allowed_methods = ["get", "delete", "put"]
        readonly = [
            "bytes_free",
            "bytes_total",
            "files_free",
            "files_total",
            "client_count",
            "mount_command",
            "mount_path",
        ]
        validation = FilesystemValidation()
        always_return_data = True

    @validate
    def obj_create(self, bundle, **kwargs):
        request = bundle.request

        filesystem_id, command_id = JobSchedulerClient.create_filesystem(bundle.data)
        filesystem = ManagedFilesystem.objects.get(pk=filesystem_id)
        command = Command.objects.get(pk=command_id)
        fs_bundle = self.full_dehydrate(self.build_bundle(obj=filesystem))
        filesystem_data = self.alter_detail_data_to_serialize(request, fs_bundle).data

        raise custom_response(
            self, request, http.HttpAccepted, {"command": dehydrate_command(command), "filesystem": filesystem_data}
        )
