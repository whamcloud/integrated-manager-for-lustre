# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.conf.urls.defaults import patterns, include
from piston.resource import Resource
from tastypie.api import Api

import monitorapi

from statsmetricapi import(GetFSTargetStats,
                           GetFSServerStats,
                           GetFSMGSStats,
                           GetServerStats,
                           GetTargetStats,
                           GetFSClientsStats,
                           GetHeatMapFSStats)


class CsrfResource(Resource):
    """CSRF protection is disabled by default in django-piston, this
       class turns it back on.

       We require CSRF protection because this API is used from a web browser.

       """
    def __init__(self, handler, authentication=None):
        super(CsrfResource, self).__init__(handler, authentication)
        self.csrf_exempt = False


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

import chroma_api.session
import chroma_api.user
import chroma_api.group

import chroma_api.volume
import chroma_api.volume_node
import chroma_api.storage_resource
import chroma_api.storage_resource_class

import chroma_api.host
import chroma_api.filesystem
import chroma_api.target
api.register(chroma_api.host.HostResource())
api.register(chroma_api.host.HostTestResource())
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
api.register(chroma_api.event.EventResource())
api.register(chroma_api.job.JobResource())
api.register(chroma_api.step.StepResource())
api.register(chroma_api.log.LogResource())
api.register(chroma_api.command.CommandResource())
api.register(chroma_api.help.HelpResource())

urlpatterns = patterns('',
    # Un-RESTful URLs pending re-work of stats store and UI
    # >>>
    (r'^api/get_fs_stats_for_targets/$', CsrfResource(GetFSTargetStats)),
    (r'^api/get_fs_stats_for_server/$', CsrfResource(GetFSServerStats)),
    (r'^api/get_fs_stats_for_mgs/$', CsrfResource(GetFSMGSStats)),
    (r'^api/get_stats_for_server/$', CsrfResource(GetServerStats)),
    (r'^api/get_stats_for_targets/$', CsrfResource(GetTargetStats)),
    (r'^api/get_fs_stats_for_client/$', CsrfResource(GetFSClientsStats)),
    (r'^api/get_fs_stats_heatmap/$', CsrfResource(GetHeatMapFSStats)),
    # <<<

    # Note: Agent API is not subject to CSRF because it is not accessed from a web browser
    (r'^api/update_scan/$', Resource(monitorapi.UpdateScan)),

    (r'^', include(api.urls)),
)
