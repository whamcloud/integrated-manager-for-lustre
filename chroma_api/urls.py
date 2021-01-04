# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.conf.urls import url, include
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

        for _, resource in api._registry.items():
            resource_klass = getattr(resource._meta, "object_class", None)
            if resource_klass and isinstance(obj, resource_klass):
                self._cache[obj.__class__] = resource
                return resource.get_resource_uri(obj)

        return None


api = ChromaApi(api_name="api")

import chroma_api.alert
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
import chroma_api.network_interface
import chroma_api.corosync

import chroma_api.host
import chroma_api.ha_cluster
import chroma_api.registration_token
import chroma_api.filesystem
import chroma_api.target
import chroma_api.nid
import chroma_api.lnet_configuration
import chroma_api.pacemaker
import chroma_api.stratagem
import chroma_api.ntp
import chroma_api.ticket

api.register(chroma_api.host.HostResource())
api.register(chroma_api.host.ServerProfileResource())
api.register(chroma_api.host.ClientMountResource())
api.register(chroma_api.host.HostTestResource())
api.register(chroma_api.registration_token.RegistrationTokenResource())
api.register(chroma_api.filesystem.FilesystemResource())
api.register(chroma_api.filesystem.OstPoolResource())
api.register(chroma_api.target.TargetResource())
api.register(chroma_api.volume.VolumeResource())
api.register(chroma_api.volume_node.VolumeNodeResource())
api.register(chroma_api.storage_resource.StorageResourceResource())
api.register(chroma_api.storage_resource_class.StorageResourceClassResource())
api.register(chroma_api.session.SessionResource())
api.register(chroma_api.session.AuthResource())
api.register(chroma_api.session.AnonAuthResource())
api.register(chroma_api.user.UserResource())
api.register(chroma_api.group.GroupResource())
api.register(chroma_api.alert.AlertResource())
api.register(chroma_api.alert.AlertTypeResource())
api.register(chroma_api.alert.AlertSubscriptionResource())
api.register(chroma_api.job.JobResource())
api.register(chroma_api.step.StepResource())
api.register(chroma_api.command.CommandResource())
api.register(chroma_api.help.HelpResource())
api.register(chroma_api.system_status.SystemStatusResource())
api.register(chroma_api.ha_cluster.HaClusterResource())
api.register(chroma_api.network_interface.NetworkInterfaceResource())
api.register(chroma_api.nid.NidResource())
api.register(chroma_api.lnet_configuration.LNetConfigurationResource())
api.register(chroma_api.corosync.CorosyncConfigurationResource())
api.register(chroma_api.pacemaker.PacemakerConfigurationResource())
api.register(chroma_api.stratagem.StratagemConfigurationResource())
api.register(chroma_api.ntp.NtpConfigurationResource())
api.register(chroma_api.ticket.TicketResource())

urlpatterns = [url(r"^", include(api.urls))]
