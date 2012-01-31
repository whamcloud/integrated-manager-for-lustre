# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

# django-piston handlers imports.
from django.conf.urls.defaults import patterns
from piston.resource import Resource

import monitorapi
from monitorapi import (GetEventsByFilter,
                        GetLatestEvents,
                        GetAlerts,
                        GetJobs,
                        GetLogs)
import configureapi
from configureapi import (GetJobStatus,
                          SetJobStatus,
                          Notifications,
                          GetTargetConfParams,
                          SetTargetConfParams)

# Stuff related to storage plugins
from configureapi import (
                         GetTargetResourceGraph)

from statsmetricapi import(GetFSTargetStats,
                           GetFSServerStats,
                           GetFSMGSStats,
                           GetServerStats,
                           GetTargetStats,
                           GetFSClientsStats,
                           GetHeatMapFSStats)

import hydraapi.host
import hydraapi.filesystem
import hydraapi.volume
import hydraapi.target
import hydraapi.storage_resource
import hydraapi.storage_resource_class


# Cross Site Referance related class
class CsrfExemptResource(Resource):
    """A Custom Resource that is csrf exempt"""
    def __init__(self, handler, authentication=None):
        super(CsrfExemptResource, self).__init__(handler, authentication)
        self.csrf_exempt = getattr(self.handler, 'csrf_exempt', True)

# hydra api urls definitions.
urlpatterns = patterns('',
    (r'^get_job_status/$', CsrfExemptResource(GetJobStatus)),
    (r'^set_job_status/$', CsrfExemptResource(SetJobStatus)),
    (r'^get_conf_params/$', CsrfExemptResource(GetTargetConfParams)),
    (r'^set_conf_params/$', CsrfExemptResource(SetTargetConfParams)),

    (r'^get_fs_stats_for_targets/$', CsrfExemptResource(GetFSTargetStats)),
    (r'^get_fs_stats_for_server/$', CsrfExemptResource(GetFSServerStats)),
    (r'^get_fs_stats_for_mgs/$', CsrfExemptResource(GetFSMGSStats)),
    (r'^get_stats_for_server/$', CsrfExemptResource(GetServerStats)),
    (r'^get_stats_for_targets/$', CsrfExemptResource(GetTargetStats)),
    (r'^get_fs_stats_for_client/$', CsrfExemptResource(GetFSClientsStats)),
    (r'^get_fs_stats_heatmap/$', CsrfExemptResource(GetHeatMapFSStats)),

    (r'^transition/$', CsrfExemptResource(configureapi.Transition)),
    (r'^transition_consequences/$', CsrfExemptResource(configureapi.TransitionConsequences)),

    (r'^geteventsbyfilter/$', CsrfExemptResource(GetEventsByFilter)),
    (r'^getlatestevents/$', CsrfExemptResource(GetLatestEvents)),
    (r'^getalerts/$', CsrfExemptResource(GetAlerts)),
    (r'^getjobs/$', CsrfExemptResource(GetJobs)),
    (r'^getlogs/$', CsrfExemptResource(GetLogs)),
    (r'^notifications/$', CsrfExemptResource(Notifications)),
    (r'^object_summary/$', CsrfExemptResource(configureapi.ObjectSummary)),


    (r'^update_scan/$', CsrfExemptResource(monitorapi.UpdateScan)),

    (r'^get_target_resource_graph/$', CsrfExemptResource(GetTargetResourceGraph)),

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

    # hydraapi.volume
    (r'^volume/$', CsrfExemptResource(hydraapi.volume.Handler)),
    (r'^volume/(?P<id>\d+)/$', CsrfExemptResource(hydraapi.volume.Handler)),
)
