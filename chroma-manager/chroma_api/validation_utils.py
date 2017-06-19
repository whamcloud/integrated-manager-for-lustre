# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


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
