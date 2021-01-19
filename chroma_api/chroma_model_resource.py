# Copyright (c) 2021 DDN. All rights reserved.
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

    def _handle_500(self, request, exception):
        log.exception(exception)

        return super(ChromaModelResource, self)._handle_500(request, exception)


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
    verbose_name=None,
    enumerations=None,
):

    base_apifield___init__(self, attribute, default, null, blank, readonly, unique, help_text, use_in)

    self.enumerations = enumerations


fields.ApiField.__init__ = apifield___init__
