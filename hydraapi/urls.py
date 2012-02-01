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
import hydraapi.help

import hydraapi.volume
import hydraapi.storage_resource
import hydraapi.storage_resource_class

import hydraapi.host
import hydraapi.filesystem
import hydraapi.target


class CsrfExemptResource(Resource):
    """A Custom Resource that is csrf exempt"""
    def __init__(self, handler, authentication=None):
        super(CsrfExemptResource, self).__init__(handler, authentication)
        self.csrf_exempt = getattr(self.handler, 'csrf_exempt', True)

urlpatterns = patterns('',
    # Un-RESTful URLs pending re-work of stats store and UI
    # >>>
    (r'^get_fs_stats_for_targets/$', CsrfExemptResource(GetFSTargetStats)),
    (r'^get_fs_stats_for_server/$', CsrfExemptResource(GetFSServerStats)),
    (r'^get_fs_stats_for_mgs/$', CsrfExemptResource(GetFSMGSStats)),
    (r'^get_stats_for_server/$', CsrfExemptResource(GetServerStats)),
    (r'^get_stats_for_targets/$', CsrfExemptResource(GetTargetStats)),
    (r'^get_fs_stats_for_client/$', CsrfExemptResource(GetFSClientsStats)),
    (r'^get_fs_stats_heatmap/$', CsrfExemptResource(GetHeatMapFSStats)),
    # <<<

    # Un-RESTful URLs pending HYD-586
    # >>>
    (r'^transition/$', CsrfExemptResource(configureapi.Transition)),
    (r'^transition_consequences/$', CsrfExemptResource(configureapi.TransitionConsequences)),
    # <<<

    # Pending HYD-523 rework of these functions (merge?)
    # >>>
    (r'^notifications/$', CsrfExemptResource(configureapi.Notifications)),
    (r'^object_summary/$', CsrfExemptResource(configureapi.ObjectSummary)),
    # <<<

    (r'^update_scan/$', CsrfExemptResource(monitorapi.UpdateScan)),

    # hydraapi.storage_resource_class
    (r'^storage_resource_class/$', CsrfExemptResource(hydraapi.storage_resource_class.StorageResourceClassHandler)),
    (r'^storage_resource_class/(?P<module_name>\w+)/(?P<class_name>\w+)/$', CsrfExemptResource(hydraapi.storage_resource_class.StorageResourceClassHandler)),

    # hydraapi.storage_resource
    (r'^storage_resource/$', CsrfExemptResource(hydraapi.storage_resource.StorageResourceHandler)),
    (r'^storage_resource/(?P<id>\d+)/$', CsrfExemptResource(hydraapi.storage_resource.StorageResourceHandler)),
    (r'^storage_resource/(?P<module_name>\w+)/(?P<class_name>\w+)/$', CsrfExemptResource(hydraapi.storage_resource.StorageResourceHandler)),

    # hydraapi.host
    (r'^host/$', CsrfExemptResource(hydraapi.host.ManagedHostsHandler)),
    (r'^host/(?P<id>\d+)/$', CsrfExemptResource(hydraapi.host.ManagedHostsHandler)),
    (r'^test_host/$', CsrfExemptResource(hydraapi.host.TestHost)),

    # hydraapi.filesystem
    (r'^filesystem/$', CsrfExemptResource(hydraapi.filesystem.FilesystemHandler)),
    (r'^filesystem/(?P<id>\d+)/$', CsrfExemptResource(hydraapi.filesystem.FilesystemHandler)),

    # hydraapi.target
    (r'^target/$', CsrfExemptResource(hydraapi.target.TargetHandler)),
    (r'^target/(?P<id>\d+)/$', CsrfExemptResource(hydraapi.target.TargetHandler)),
    (r'^target/(?P<id>\d+)/resource_graph/$', CsrfExemptResource(hydraapi.target.TargetResourceGraphHandler)),

    # hydraapi.volume
    (r'^volume/$', CsrfExemptResource(hydraapi.volume.Handler)),
    (r'^volume/(?P<id>\d+)/$', CsrfExemptResource(hydraapi.volume.Handler)),

    # hydraapi.alert
    (r'^alert/$', CsrfExemptResource(hydraapi.alert.Handler)),

    # hydraapi.event
    (r'^event/$', CsrfExemptResource(hydraapi.event.Handler)),

    # hydraapi.log
    (r'^log/$', CsrfExemptResource(hydraapi.log.Handler)),

    # hydraapi.job
    (r'^job/$', CsrfExemptResource(hydraapi.job.Handler)),
    (r'^job/(?P<id>\d+)/$', CsrfExemptResource(hydraapi.job.Handler)),

    # hydraapi.help
    (r'^help/conf_param/$', CsrfExemptResource(hydraapi.help.ConfParamHandler)),
)
