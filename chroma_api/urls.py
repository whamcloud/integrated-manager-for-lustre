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
)
