# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from tastypie.exceptions import ImmediateHttpResponse
from tastypie.resources import ModelResource
from tastypie import fields

from chroma_core.services import log_register

log = log_register(__name__)


class ChromaModelResource(ModelResource):
    """
    Base class for chroma_models.
    """

    ALL_FILTER_INT = ["exact", "gte", "lte", "gt", "lt"]
    ALL_FILTER_STR = ["contains", "exact", "startswith", "endswith"]
    ALL_FILTER_DATE = ["exact", "gte", "lte", "gt", "lt"]
    ALL_FILTER_ENUMERATION = ["exact", "contains", "startswith", "endswith", "in"]
    ALL_FILTER_BOOL = ["exact"]

    # Add the enumeration type to the schema info.
    def build_schema(self):
        """
        Returns a dictionary of all the fields on the resource and some
        properties about those fields.

        Used by the ``schema/`` endpoint to describe what will be available.
        """

        data = super(ChromaModelResource, self).build_schema()

        # Add enumeration
        for field_name, field_object in self.fields.items():
            if getattr(field_object, "enumerations", None):
                data["fields"][field_name]["enumeration"] = field_object.enumerations

        return data

    def obj_update(self, bundle, **kwargs):
        self.is_valid(bundle)

        if bundle.errors:
            raise ImmediateHttpResponse(
                response=self.error_response(bundle.request, bundle.errors[self._meta.resource_name])
            )

        return ModelResource.obj_update(self, bundle, **kwargs)

    def obj_create(self, bundle, **kwargs):
        self.is_valid(bundle)

        if bundle.errors:
            raise ImmediateHttpResponse(
                response=self.error_response(bundle.request, bundle.errors[self._meta.resource_name])
            )

        return ModelResource.obj_create(self, bundle, **kwargs)


# Add enumeration type to the fields
base_apifield___init__ = fields.ApiField.__init__


def apifield___init__(
    self,
    attribute=None,
    default=fields.NOT_PROVIDED,
    null=False,
    blank=False,
    readonly=False,
    unique=False,
    help_text=None,
    use_in="all",
    enumerations=None,
):

    base_apifield___init__(self, attribute, default, null, blank, readonly, unique, help_text, use_in)

    self.enumerations = enumerations


fields.ApiField.__init__ = apifield___init__
