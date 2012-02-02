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

import hydraapi.alert
import hydraapi.event
import hydraapi.log
import hydraapi.job
import hydraapi.command
import hydraapi.help

import hydraapi.volume
import hydraapi.volume_node
import hydraapi.storage_resource
import hydraapi.storage_resource_class

import hydraapi.host
import hydraapi.filesystem
import hydraapi.target


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

    # hydraapi.storage_resource_class
    (r'^storage_resource_class/$', CsrfResource(hydraapi.storage_resource_class.StorageResourceClassHandler)),
    (r'^storage_resource_class/(?P<module_name>\w+)/(?P<class_name>\w+)/$', CsrfResource(hydraapi.storage_resource_class.StorageResourceClassHandler)),

    # hydraapi.storage_resource
    (r'^storage_resource/$', CsrfResource(hydraapi.storage_resource.StorageResourceHandler)),
    (r'^storage_resource/(?P<id>\d+)/$', CsrfResource(hydraapi.storage_resource.StorageResourceHandler)),
    (r'^storage_resource/(?P<module_name>\w+)/(?P<class_name>\w+)/$', CsrfResource(hydraapi.storage_resource.StorageResourceHandler)),

    # hydraapi.host
    (r'^host/$', CsrfResource(hydraapi.host.ManagedHostsHandler)),
    (r'^host/(?P<id>\d+)/$', CsrfResource(hydraapi.host.ManagedHostsHandler)),
    (r'^test_host/$', CsrfResource(hydraapi.host.TestHost)),

    # hydraapi.filesystem
    (r'^filesystem/$', CsrfResource(hydraapi.filesystem.FilesystemHandler)),
    (r'^filesystem/(?P<id>\d+)/$', CsrfResource(hydraapi.filesystem.FilesystemHandler)),

    # hydraapi.target
    (r'^target/$', CsrfResource(hydraapi.target.TargetHandler)),
    (r'^target/(?P<id>\d+)/$', CsrfResource(hydraapi.target.TargetHandler)),
    (r'^target/(?P<id>\d+)/resource_graph/$', CsrfResource(hydraapi.target.TargetResourceGraphHandler)),

    # hydraapi.volume
    (r'^volume/$', CsrfResource(hydraapi.volume.Handler)),
    (r'^volume/(?P<id>\d+)/$', CsrfResource(hydraapi.volume.Handler)),

    # hydraapi.volume_node
    (r'^volume_node/$', CsrfResource(hydraapi.volume_node.Handler)),

    # hydraapi.alert
    (r'^alert/$', CsrfResource(hydraapi.alert.Handler)),

    # hydraapi.event
    (r'^event/$', CsrfResource(hydraapi.event.Handler)),

    # hydraapi.log
    (r'^log/$', CsrfResource(hydraapi.log.Handler)),

    # hydraapi.command
    (r'^command/(?P<id>\d+)/$', CsrfResource(hydraapi.command.Handler)),

    # hydraapi.job
    (r'^job/$', CsrfResource(hydraapi.job.Handler)),
    (r'^job/(?P<id>\d+)/$', CsrfResource(hydraapi.job.Handler)),

    # hydraapi.help
    (r'^help/conf_param/$', CsrfResource(hydraapi.help.ConfParamHandler)),
)
