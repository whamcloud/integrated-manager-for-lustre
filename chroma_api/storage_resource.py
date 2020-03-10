# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import defaultdict
from django.contrib.contenttypes.models import ContentType
from tastypie.validation import Validation
from chroma_core.lib.storage_plugin.api import attributes, statistics
from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource

from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from tastypie import fields
from chroma_core.lib.storage_plugin.query import ResourceQuery
from chroma_api.utils import MetricResource
from chroma_api.validation_utils import validate

from tastypie.exceptions import NotFound, ImmediateHttpResponse
from tastypie import http
from django.core.exceptions import ObjectDoesNotExist

from chroma_api.storage_resource_class import filter_class_ids
from chroma_api.chroma_model_resource import ChromaModelResource


from chroma_core.services.plugin_runner.scan_daemon_interface import ScanDaemonRpcInterface


class StorageResourceValidation(Validation):
    def is_valid(self, bundle, request=None):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        from chroma_core.lib.storage_plugin.manager import PluginNotFound

        errors = defaultdict(list)
        if "alias" in bundle.data and bundle.data["alias"] is not None:
            alias = bundle.data["alias"]
            if alias.strip() == "":
                errors["alias"].append("May not be blank")
            elif alias != alias.strip():
                errors["alias"].append("No trailing whitespace allowed")

        if "plugin_name" in bundle.data:
            try:
                storage_plugin_manager.get_plugin_class(bundle.data["plugin_name"])
            except PluginNotFound as e:
                errors["plugin_name"].append(e.__str__())
            else:
                if "class_name" in bundle.data:
                    try:
                        storage_plugin_manager.get_plugin_resource_class(
                            bundle.data["plugin_name"], bundle.data["class_name"]
                        )
                    except PluginNotFound as e:
                        errors["class_name"].append(e.__str__())

        return errors
