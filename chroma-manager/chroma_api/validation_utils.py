#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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


from collections import defaultdict
from collections import namedtuple
from tastypie.validation import Validation
from tastypie.exceptions import NotFound

from chroma_core.services import log_register

log = log_register(__name__)


class ChromaValidation(Validation):
    '''
    Helper class to allow common chroma validation to be pulled together into one place. As of time of writing we are
    weak on validation and so this is a first small step towards helping fix that.
    '''
    Expectation = namedtuple('Expectations', ['required'])
    URIInfo = namedtuple('URIInfo', ['uri', 'expected_type'])

    mandatory_message = "This field is mandatory"

    def validate_object(self, object, errors, expectation):
        '''
        Quick object checker, allows to check that required items are present, and other stray items are not, in future we
        will add types etc.
        :param object: Object to be checked.
        :param errors: Array to append errors to.
        :param expectation: Dictionary of known fields with nametuple (Expectation) of attributes
        :return: True if errors found else False
        '''

        assert type(errors) == defaultdict

        error_found = False

        object = dict(object)

        for key, value in expectation.items():
            if value.required and key not in object:
                error_found = True
                errors[key].append("Field %s not present in data" % key)

            object.pop(key, None)

        if len(object):
            error_found = True
            errors[",".join(object.keys())].append("Additional field(s) %s found in data" % ",".join(object.keys()))

        return error_found

    def validate_resources(self, resource_uris, errors):
        '''
        Simply validates the uri string passed in are valid and return the correct type.
        :param resource_uris: List of uri's to validate
        :param errors: Array to append errors to.
        :return: True if errors found else False
        '''

        assert type(errors) == defaultdict

        error_found = False

        for resource_uri in resource_uris:
            if resource_uri.uri:                    # uri can be none meaning the resource is not expected.
                try:
                    resource_uri.expected_type().get_via_uri(resource_uri.uri)
                except (NotFound, resource_uri.expected_type.Meta.object_class.DoesNotExist):
                    error_found = True
                    errors[resource_uri.uri].append("Resource %s was not found" % resource_uri.uri)

        return error_found
