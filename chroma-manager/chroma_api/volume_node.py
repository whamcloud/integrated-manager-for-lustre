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


from chroma_core.models import VolumeNode
from tastypie.resources import ModelResource

from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication

from tastypie import fields


class VolumeNodeResource(ModelResource):
    """
    Represents a device node on a particular host, which
    accesses a particular volume.  Usually accessed
    as an attribute of a volume rather than on its own.

    This resource cannot be written to directly.  To update
    ``use`` and ``primary``, PUT to the volume that the
    node belongs to.

    This resource is used by the CLI
    """

    volume_id = fields.IntegerField(attribute = 'volume_id',
                                    help_text = "id of the volume that this node belongs to")
    host_id = fields.IntegerField(help_text = "id of the host that this\
            device node is on")
    host_label = fields.CharField(help_text = "label attribute of the \
            host that this device node is on, as a convenience \
            for presentation")
    host = fields.ToOneField('chroma_api.host.HostResource', 'host')

    def dehydrate_host_id(self, bundle):
        return bundle.obj.host.id

    def dehydrate_host_label(self, bundle):
        return bundle.obj.host.get_label()

    class Meta:
        queryset = VolumeNode.objects.all().select_related("host")
        resource_name = 'volume_node'
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ['not_deleted']
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        filtering = {'host': ['exact'], 'path': ['exact']}
