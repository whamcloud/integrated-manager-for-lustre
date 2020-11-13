# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import defaultdict
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from chroma_core.models import ManagedFilesystem, ManagedTarget
from chroma_core.models import ManagedOst, ManagedMdt, ManagedMgs
from chroma_core.models import Volume, VolumeNode
from chroma_core.models import Command, OstPool
from chroma_core.models.filesystem import HSM_CONTROL_KEY, HSM_CONTROL_PARAMS

import tastypie.http as http
from tastypie import fields
from tastypie.exceptions import NotFound
from tastypie.validation import Validation
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.chroma_model_resource import ChromaModelResource
from chroma_api.utils import custom_response, ConfParamResource, dehydrate_command
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


class FilesystemResource(ConfParamResource):
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
        attribute=lambda bundle: ManagedMdt.objects.filter(filesystem=bundle.obj),
        help_text="List of MDTs in this file system, should be at least 1 unless the "
        "file system is in the process of being deleted",
    )
    mgt = fields.ToOneField(
        "chroma_api.target.TargetResource",
        attribute="mgs",
        help_text="The MGT on which this file system is registered",
    )

    def dehydrate_mount_path(self, bundle):
        return bundle.obj.mount_path()

    def dehydrate_mount_command(self, bundle):
        path = self.dehydrate_mount_path(bundle)
        if path:
            return "mount -t lustre %s /mnt/%s" % (path, bundle.obj.name)
        else:
            return None

    class Meta:
        queryset = ManagedFilesystem.objects.all()
        resource_name = "filesystem"
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ["not_deleted", "ost_next_index", "mdt_next_index"]
        ordering = ["name"]
        filtering = {"id": ["exact", "in"], "name": ["exact"]}
        list_allowed_methods = ["get", "post"]
        detail_allowed_methods = ["get", "delete", "put"]
        readonly = [
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


class OstPoolResource(ChromaModelResource):
    osts = fields.ToManyField(
        "chroma_api.target.TargetResource",
        "osts",
        null=True,
        help_text="List of OSTs in this Pool",
    )
    filesystem = fields.ToOneField("chroma_api.filesystem.FilesystemResource", "filesystem")

    class Meta:
        queryset = OstPool.objects.all()
        resource_name = "ostpool"
        authentication = AnonymousAuthentication()
        authorization = PatchedDjangoAuthorization()
        excludes = ["not_deleted"]
        ordering = ["filesystem", "name"]
        list_allowed_methods = ["get", "delete", "put", "post"]
        detail_allowed_methods = ["get", "put", "delete"]
        filtering = {"filesystem": ["exact"], "name": ["exact"], "id": ["exact"]}

    # POST handler
    @validate
    def obj_create(self, bundle, **kwargs):
        request = bundle.request

        ostpool_id, command_id = JobSchedulerClient.create_ostpool(bundle.data)
        command = Command.objects.get(pk=command_id)

        raise custom_response(self, request, http.HttpAccepted, {"command": dehydrate_command(command)})

    # PUT handler
    @validate
    def obj_update(self, bundle, **kwargs):
        try:
            obj = self.obj_get(bundle, **kwargs)
        except ObjectDoesNotExist:
            raise NotFound("A model instance matching the provided arguments could not be found.")

        command_id = JobSchedulerClient.update_ostpool(bundle.data)
        command = Command.objects.get(pk=command_id)

        raise custom_response(self, bundle.request, http.HttpAccepted, {"command": dehydrate_command(command)})

    # DELETE handlers
    def _pool_delete(self, request, obj_list):
        commands = []
        for obj in obj_list:
            command_id = JobSchedulerClient.delete_ostpool(obj.id)
            command = Command.objects.get(pk=command_id)
            commands.append(dehydrate_command(command))
        raise custom_response(self, request, http.HttpAccepted, {"commands": commands})

    def obj_delete(self, bundle, **kwargs):
        try:
            obj = self.obj_get(bundle, **kwargs)
        except ObjectDoesNotExist:
            raise NotFound("A model instance matching the provided arguments could not be found.")
        self._pool_delete(bundle.request, [obj])

    def obj_delete_list(self, bundle, **kwargs):
        try:
            obj_list = self.obj_get_list(bundle, **kwargs)
        except ObjectDoesNotExist:
            raise NotFound("A model instance matching the provided arguments could not be found.")
        self._pool_delete(bundle.request, obj_list)
