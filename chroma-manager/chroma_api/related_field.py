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


from tastypie.fields import RelatedField


def dehydrate_related(self, bundle, related_resource):
    """
    Based on the ``full_resource``, returns either the endpoint or the data
    from ``full_dehydrate`` for the related resource.

    Allows the definition to be overridden by a parameter such as nid_dehydrate={True/False}
    """

    # For some reason resource_name is not always present for all objects. Needs to be understood but
    # it only happens in test when some of the objects have been faked so probably something we can come back to.
    dehydrate_flag_name = "dehydrate__" + getattr(related_resource.Meta, 'resource_name', "no_resource_name")

    dehydrate_flag_value = bundle.request.GET.get(dehydrate_flag_name, self.full)

    # Now normalize it to actually be a boolean.
    dehydrate = dehydrate_flag_value not in [False, 'false', 'False', 0, '0', None]

    if not dehydrate:
        # Be a good netizen.
        return related_resource.get_resource_uri(bundle)
    else:
        # ZOMG extra data and big payloads.
        bundle = related_resource.build_bundle(obj=related_resource.instance, request=bundle.request)

        # We have to be careful of recursive expansions caused by users flags, so remove flag
        # before call but replace it afterwards.
        # You have to preserved the original and pop from the copy because the original is immutable.
        args_safe = bundle.request.GET
        bundle.request.GET = args_safe.copy()
        bundle.request.GET.pop(dehydrate_flag_name, None)

        result = related_resource.full_dehydrate(bundle)

        bundle.request.GET = args_safe

        return result


RelatedField.dehydrate_related = dehydrate_related
