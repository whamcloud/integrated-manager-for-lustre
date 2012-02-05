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

import chroma_api.alert
import chroma_api.event
import chroma_api.log
import chroma_api.job
import chroma_api.command
import chroma_api.help

import chroma_api.volume
import chroma_api.volume_node
import chroma_api.storage_resource
import chroma_api.storage_resource_class

import chroma_api.host
import chroma_api.filesystem
import chroma_api.target


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

    # chroma_api.storage_resource_class
    (r'^storage_resource_class/$', CsrfExemptResource(chroma_api.storage_resource_class.StorageResourceClassHandler)),
    (r'^storage_resource_class/(?P<module_name>\w+)/(?P<class_name>\w+)/$', CsrfExemptResource(chroma_api.storage_resource_class.StorageResourceClassHandler)),

    # chroma_api.storage_resource
    (r'^storage_resource/$', CsrfExemptResource(chroma_api.storage_resource.StorageResourceHandler)),
    (r'^storage_resource/(?P<id>\d+)/$', CsrfExemptResource(chroma_api.storage_resource.StorageResourceHandler)),
    (r'^storage_resource/(?P<module_name>\w+)/(?P<class_name>\w+)/$', CsrfExemptResource(chroma_api.storage_resource.StorageResourceHandler)),

    # chroma_api.host
    (r'^host/$', CsrfExemptResource(chroma_api.host.ManagedHostsHandler)),
    (r'^host/(?P<id>\d+)/$', CsrfExemptResource(chroma_api.host.ManagedHostsHandler)),
    (r'^test_host/$', CsrfExemptResource(chroma_api.host.TestHost)),

    # chroma_api.filesystem
    (r'^filesystem/$', CsrfExemptResource(chroma_api.filesystem.FilesystemHandler)),
    (r'^filesystem/(?P<id>\d+)/$', CsrfExemptResource(chroma_api.filesystem.FilesystemHandler)),

    # chroma_api.target
    (r'^target/$', CsrfExemptResource(chroma_api.target.TargetHandler)),
    (r'^target/(?P<id>\d+)/$', CsrfExemptResource(chroma_api.target.TargetHandler)),
    (r'^target/(?P<id>\d+)/resource_graph/$', CsrfExemptResource(chroma_api.target.TargetResourceGraphHandler)),

    # chroma_api.volume
    (r'^volume/$', CsrfExemptResource(chroma_api.volume.Handler)),
    (r'^volume/(?P<id>\d+)/$', CsrfExemptResource(chroma_api.volume.Handler)),

    # chroma_api.volume_node
    (r'^volume_node/$', CsrfExemptResource(chroma_api.volume_node.Handler)),

    # chroma_api.alert
    (r'^alert/$', CsrfExemptResource(chroma_api.alert.Handler)),

    # chroma_api.event
    (r'^event/$', CsrfExemptResource(chroma_api.event.Handler)),

    # chroma_api.log
    (r'^log/$', CsrfExemptResource(chroma_api.log.Handler)),

    # chroma_api.command
    (r'^command/(?P<id>\d+)/$', CsrfExemptResource(chroma_api.command.Handler)),

    # chroma_api.job
    (r'^job/$', CsrfExemptResource(chroma_api.job.Handler)),
    (r'^job/(?P<id>\d+)/$', CsrfExemptResource(chroma_api.job.Handler)),

    # chroma_api.help
    (r'^help/conf_param/$', CsrfExemptResource(chroma_api.help.ConfParamHandler)),
)
