# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.models.host import Volume, VolumeNode
from chroma_core.models.target import FilesystemMember
import chroma_core.lib.conf_param
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from collections import defaultdict
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from chroma_core.models import ManagedOst, ManagedMdt, ManagedMgs, ManagedTarget, ManagedFilesystem
import tastypie.http as http
from tastypie.utils import dict_strip_unicode_keys
from tastypie.validation import Validation
from tastypie.resources import BadRequest, ImmediateHttpResponse
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.utils import custom_response, ConfParamResource, dehydrate_command
from chroma_api.validation_utils import validate

# Some lookups for the three 'kind' letter strings used
# by API consumers to refer to our target types
KIND_TO_KLASS = {"MGT": ManagedMgs, "OST": ManagedOst, "MDT": ManagedMdt}
KIND_TO_MODEL_NAME = dict([(k, v.__name__.lower()) for k, v in KIND_TO_KLASS.items()])


class TargetValidation(Validation):
    def _validate_post(self, bundle, request):
        errors = defaultdict(list)

        for mandatory_field in ["kind", "volume_id"]:
            if mandatory_field not in bundle.data or bundle.data[mandatory_field] == None:
                errors[mandatory_field].append("This field is mandatory")

        if errors:
            return errors

        volume_id = bundle.data["volume_id"]
        try:
            volume = Volume.objects.get(id=volume_id)
        except Volume.DoesNotExist:
            errors["volume_id"].append("Volume %s not found" % volume_id)
        else:
            if ManagedTarget.objects.filter(volume=volume).count():
                errors["volume_id"].append("Volume %s in use" % volume_id)

        kind = bundle.data["kind"]
        if not kind in KIND_TO_KLASS:
            errors["kind"].append(
                "Invalid target type '%s' (choose from [%s])" % (kind, ",".join(KIND_TO_KLASS.keys()))
            )
        else:
            if issubclass(KIND_TO_KLASS[kind], FilesystemMember):
                if not "filesystem_id" in bundle.data:
                    errors["filesystem_id"].append("Mandatory for targets of kind '%s'" % kind)
                else:
                    filesystem_id = bundle.data["filesystem_id"]
                    try:
                        filesystem = ManagedFilesystem.objects.get(id=filesystem_id)
                    except ManagedFilesystem.DoesNotExist:
                        errors["filesystem_id"].append("Filesystem %s not found" % filesystem_id)
                    else:
                        if filesystem.immutable_state:
                            errors["filesystem_id"].append("Filesystem %s is unmanaged" % filesystem.name)

            if KIND_TO_KLASS[kind] == ManagedMgs:
                mgt_volume = Volume.objects.get(id=volume_id)
                hosts = [vn.host for vn in VolumeNode.objects.filter(volume=mgt_volume, use=True)]
                conflicting_mgs_count = ManagedTarget.objects.filter(
                    ~Q(managedmgs=None), managedtargetmount__host__in=hosts
                ).count()
                if conflicting_mgs_count > 0:
                    errors["mgt"].append(
                        "Volume %s cannot be used for MGS (only one MGS is allowed per server)" % mgt_volume.label
                    )

                if "filesystem_id" in bundle.data:
                    bundle.data_errors["filesystem_id"].append("Cannot specify filesystem_id when creating MGT")

            if "conf_params" in bundle.data:
                conf_param_errors = chroma_core.lib.conf_param.validate_conf_params(
                    KIND_TO_KLASS[kind], bundle.data["conf_params"]
                )
                if conf_param_errors:
                    errors["conf_params"] = conf_param_errors

        try:
            errors.update(bundle.data_errors)
        except AttributeError:
            pass

        return errors

    def _validate_put(self, bundle, request):
        errors = defaultdict(list)
        if "conf_params" in bundle.data and bundle.data["conf_params"] is not None:
            try:
                target_klass = KIND_TO_KLASS[bundle.data["kind"]]
            except KeyError:
                errors["kind"].append("Must be one of %s" % KIND_TO_KLASS.keys())
            else:
                try:
                    target = target_klass.objects.get(pk=bundle.data["id"])
                except KeyError:
                    errors["id"].append("Field is mandatory")
                except target_klass.DoesNotExist:
                    errors["id"].append("No %s with ID %s found" % (target_klass.__name__, bundle.data["id"]))
                else:

                    if target.immutable_state:
                        # Check that the conf params are unmodified
                        existing_conf_params = chroma_core.lib.conf_param.get_conf_params(target)
                        if not chroma_core.lib.conf_param.compare(existing_conf_params, bundle.data["conf_params"]):
                            errors["conf_params"].append("Cannot modify conf_params on immutable_state objects")
                    else:
                        conf_param_errors = chroma_core.lib.conf_param.validate_conf_params(
                            target_klass, bundle.data["conf_params"]
                        )
                        if conf_param_errors:
                            errors["conf_params"] = conf_param_errors
        return errors

    def is_valid(self, bundle, request=None):
        if request.method == "POST":
            return self._validate_post(bundle, request)
        elif request.method == "PUT":
            return self._validate_put(bundle, request)
        else:
            return {}


class TargetResource(ConfParamResource):
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

    class Meta:
        # ManagedTarget is a Polymorphic Model which gets related
        # to content_type in the __metaclass__
        queryset = ManagedTarget.objects.all()
        resource_name = "target"
        excludes = ["not_deleted", "bytes_per_inode", "reformat"]
        filtering = {
            "id": ["exact", "in"],
            "immutable_state": ["exact"],
            "name": ["exact"],
        }
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        ordering = ["name"]
        list_allowed_methods = ["get", "post", "patch"]
        detail_allowed_methods = ["get", "put", "delete"]
        validation = TargetValidation()
        always_return_data = True
        readonly = [
            "filesystems",
            "name",
            "uuid",
            "ha_label",
            "filesystem_name",
            "filesystem_id",
        ]

    def patch_list(self, request, **kwargs):
        """
        Specialization of patch_list to do bulk target creation in a single RPC to job_scheduler (and
        consequently in a single command).
        """
        deserialized = self.deserialize(
            request, request.body, format=request.META.get("CONTENT_TYPE", "application/json")
        )

        if "objects" not in deserialized:
            raise BadRequest("Invalid data sent.")

        if len(deserialized["objects"]) and "put" not in self._meta.detail_allowed_methods:
            raise ImmediateHttpResponse(response=http.HttpMethodNotAllowed())

        # If any of the included targets is not a creation, then
        # skip to a normal PATCH instead of this special case one
        for target_data in deserialized["objects"]:
            if "id" in target_data or "resource_uri" in target_data:
                super(TargetResource, self).patch_list(request, **kwargs)

        # Validate and prepare each target dict for consumption by job_scheduler
        for target_data in deserialized["objects"]:
            data = self.alter_deserialized_detail_data(request, target_data)
            bundle = self.build_bundle(data=dict_strip_unicode_keys(data))
            bundle.request = request
            self.is_valid(bundle)

            target_data["content_type"] = ContentType.objects.get_for_model(
                KIND_TO_KLASS[target_data["kind"]]
            ).natural_key()

        targets, command = JobSchedulerClient.create_targets(deserialized["objects"])

        raise custom_response(
            self,
            request,
            http.HttpAccepted,
            {"command": dehydrate_command(command), "targets": [self.get_resource_uri(target) for target in targets]},
        )

    @validate
    def obj_create(self, bundle, **kwargs):
        request = bundle.request

        self.is_valid(bundle)

        if bundle.errors:
            raise ImmediateHttpResponse(
                response=self.error_response(bundle.request, bundle.errors[self._meta.resource_name])
            )

        # Set up an errors dict in the bundle to allow us to carry
        # hydration errors through to validation.
        setattr(bundle, "data_errors", defaultdict(list))

        bundle.data["content_type"] = ContentType.objects.get_for_model(
            KIND_TO_KLASS[bundle.data["kind"]]
        ).natural_key()

        # Should really only be doing one validation pass, but this works
        # OK for now.  It's better than raising a 404 or duplicating the
        # filesystem validation failure if it doesn't exist, anyhow.
        self.is_valid(bundle)

        targets, command = JobSchedulerClient.create_targets([bundle.data])

        if request.method == "POST":
            raise custom_response(
                self,
                request,
                http.HttpAccepted,
                {
                    "command": dehydrate_command(command),
                    "target": self.full_dehydrate(self.build_bundle(obj=targets[0])).data,
                },
            )
