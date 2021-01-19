# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import chroma_core.lib.conf_param
from collections import defaultdict
from chroma_core.models import ManagedOst, ManagedMdt, ManagedMgs, ManagedTarget
from tastypie.validation import Validation
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.utils import ConfParamResource

# Some lookups for the three 'kind' letter strings used
# by API consumers to refer to our target types
KIND_TO_KLASS = {"MGT": ManagedMgs, "OST": ManagedOst, "MDT": ManagedMdt}
KIND_TO_MODEL_NAME = dict([(k, v.__name__.lower()) for k, v in KIND_TO_KLASS.items()])


class TargetValidation(Validation):
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
        if request.method == "PUT":
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
        list_allowed_methods = ["get"]
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
