#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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

from tastypie.resources import ModelResource
from tastypie import fields

from chroma_core.services import log_register

log = log_register(__name__)


class ChromaModelResource(ModelResource):
    """
    Base class for chroma_models.
    """

    ALL_FILTER_INT = ['exact', 'gte', 'lte', 'gt', 'lt']
    ALL_FILTER_STR = ['contains', 'exact', 'startswith', 'endswith']
    ALL_FILTER_DATE = ['exact', 'gte', 'lte', 'gt', 'lt']
    ALL_FILTER_ENUMERATION = ['exact', 'contains', 'startswith', 'endswith', 'in']
    ALL_FILTER_BOOL = ['exact']

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
            if getattr(field_object, 'enumerations', None):
                data['fields'][field_name]['enumeration'] = field_object.enumerations

        return data

# Add enumeration type to the fields
base_apifield___init__ = fields.ApiField.__init__


def apifield___init__(self,
                      attribute=None,
                      default=fields.NOT_PROVIDED,
                      null=False,
                      blank=False,
                      readonly=False,
                      unique=False,
                      help_text=None,
                      enumerations=None):

    base_apifield___init__(self, attribute, default, null, blank, readonly, unique, help_text)

    self.enumerations = enumerations


fields.ApiField.__init__ = apifield___init__
