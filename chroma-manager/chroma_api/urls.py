#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


from django.conf.urls.defaults import patterns, include
from tastypie.api import Api


class ChromaApi(Api):
    def __init__(self, *args, **kwargs):
        self._cache = {}
        super(ChromaApi, self).__init__(*args, **kwargs)

    def get_resource_uri(self, obj):
        """Resolve the class of ``obj`` to a Resource and
           call its get_resource_uri function."""
        try:
            return self._cache[obj.__class__].get_resource_uri(obj)
        except KeyError:
            pass

        for resource_name, resource in api._registry.items():
            resource_klass = getattr(resource._meta, 'object_class', None)
            if resource_klass and isinstance(obj, resource_klass):
                self._cache[obj.__class__] = resource
                return resource.get_resource_uri(obj)

        return None

api = ChromaApi(api_name = 'api')

import chroma_api.alert
import chroma_api.event
import chroma_api.log
import chroma_api.job
import chroma_api.step
import chroma_api.command
import chroma_api.help
import chroma_api.system_status

import chroma_api.session
import chroma_api.user
import chroma_api.group

import chroma_api.volume
import chroma_api.volume_node
import chroma_api.storage_resource
import chroma_api.storage_resource_class

import chroma_api.power_control

import chroma_api.host
import chroma_api.ha_cluster
import chroma_api.registration_token
import chroma_api.filesystem
import chroma_api.target
import chroma_api.package
import chroma_api.client_error
import chroma_api.notification

api.register(chroma_api.host.HostResource())
api.register(chroma_api.host.ServerProfileResource())
api.register(chroma_api.host.ClientMountResource())
api.register(chroma_api.host.HostTestResource())
api.register(chroma_api.registration_token.RegistrationTokenResource())
api.register(chroma_api.filesystem.FilesystemResource())
api.register(chroma_api.target.TargetResource())
api.register(chroma_api.volume.VolumeResource())
api.register(chroma_api.volume_node.VolumeNodeResource())
api.register(chroma_api.storage_resource.StorageResourceResource())
api.register(chroma_api.storage_resource_class.StorageResourceClassResource())
api.register(chroma_api.session.SessionResource())
api.register(chroma_api.user.UserResource())
api.register(chroma_api.group.GroupResource())
api.register(chroma_api.alert.AlertResource())
api.register(chroma_api.alert.AlertTypeResource())
api.register(chroma_api.alert.AlertSubscriptionResource())
api.register(chroma_api.event.EventResource())
api.register(chroma_api.job.JobResource())
api.register(chroma_api.step.StepResource())
api.register(chroma_api.log.LogResource())
api.register(chroma_api.command.CommandResource())
api.register(chroma_api.help.HelpResource())
api.register(chroma_api.system_status.SystemStatusResource())
api.register(chroma_api.ha_cluster.HaClusterResource())
api.register(chroma_api.power_control.PowerControlTypeResource())
api.register(chroma_api.power_control.PowerControlDeviceResource())
api.register(chroma_api.power_control.PowerControlDeviceOutletResource())
api.register(chroma_api.package.PackageResource())
api.register(chroma_api.client_error.ClientErrorResource())
api.register(chroma_api.notification.NotificationResource())

urlpatterns = patterns('',
    (r'^', include(api.urls)),
)
