# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

# django-piston handlers imports.
from django.conf.urls.defaults import patterns
from piston.resource import Resource

import monitorapi
import configureapi

from statsmetricapi import(GetFSTargetStats,
                           GetFSServerStats,
                           GetFSMGSStats,
                           GetServerStats,
                           GetTargetStats,
                           GetFSClientsStats,
                           GetHeatMapFSStats)


import chroma_api.storage_resource
import chroma_api.storage_resource_class


class CsrfResource(Resource):
    """CSRF protection is disabled by default in django-piston, this
       class turns it back on.

       We require CSRF protection because this API is used from a web browser.

       """
    def __init__(self, handler, authentication=None):
        super(CsrfResource, self).__init__(handler, authentication)
        self.csrf_exempt = False

urlpatterns = patterns('',
    # Un-RESTful URLs pending re-work of stats store and UI
    # >>>
    (r'^get_fs_stats_for_targets/$', CsrfResource(GetFSTargetStats)),
    (r'^get_fs_stats_for_server/$', CsrfResource(GetFSServerStats)),
    (r'^get_fs_stats_for_mgs/$', CsrfResource(GetFSMGSStats)),
    (r'^get_stats_for_server/$', CsrfResource(GetServerStats)),
    (r'^get_stats_for_targets/$', CsrfResource(GetTargetStats)),
    (r'^get_fs_stats_for_client/$', CsrfResource(GetFSClientsStats)),
    (r'^get_fs_stats_heatmap/$', CsrfResource(GetHeatMapFSStats)),
    # <<<

    # Un-RESTful URLs pending HYD-586
    # >>>
    (r'^transition/$', CsrfResource(configureapi.Transition)),
    (r'^transition_consequences/$', CsrfResource(configureapi.TransitionConsequences)),
    # <<<

    # Pending HYD-523 rework of these functions (merge?)
    # >>>
    (r'^notifications/$', CsrfResource(configureapi.Notifications)),
    (r'^object_summary/$', CsrfResource(configureapi.ObjectSummary)),
    # <<<

    # Note: Agent API is not subject to CSRF because it is not accessed from a web browser
    (r'^update_scan/$', Resource(monitorapi.UpdateScan)),

    # chroma_api.storage_resource_class
    (r'^storage_resource_class/$', CsrfResource(chroma_api.storage_resource_class.StorageResourceClassHandler)),
    (r'^storage_resource_class/(?P<module_name>\w+)/(?P<class_name>\w+)/$', CsrfResource(chroma_api.storage_resource_class.StorageResourceClassHandler)),

    # chroma_api.storage_resource
    (r'^storage_resource/$', CsrfResource(chroma_api.storage_resource.StorageResourceHandler)),
    (r'^storage_resource/(?P<id>\d+)/$', CsrfResource(chroma_api.storage_resource.StorageResourceHandler)),
    (r'^storage_resource/(?P<module_name>\w+)/(?P<class_name>\w+)/$', CsrfResource(chroma_api.storage_resource.StorageResourceHandler)),
)
