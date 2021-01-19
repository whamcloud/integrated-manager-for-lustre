# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from tastypie.fields import RelatedField


def dehydrate_related(self, bundle, related_resource, for_list=True):
    """
    Based on the ``full_resource``, returns either the endpoint or the data
    from ``full_dehydrate`` for the related resource.

    Allows the definition to be overridden by a parameter such as dehydrate__nid={True/False}
    """

    dehydrate_flag_name = "dehydrate__" + self.instance_name

    should_dehydrate_full_resource = self.should_full_dehydrate(bundle, for_list=for_list)

    dehydrate_flag_value = bundle.request.GET.get(dehydrate_flag_name, should_dehydrate_full_resource)

    # Now normalize it to actually be a boolean.
    dehydrate = dehydrate_flag_value not in [False, "false", "False", 0, "0", None]

    if not dehydrate:
        # Be a good netizen.
        return related_resource.get_resource_uri(bundle)

    # ZOMG extra data and big payloads.
    bundle = related_resource.build_bundle(obj=bundle.obj, request=bundle.request, objects_saved=bundle.objects_saved)

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
