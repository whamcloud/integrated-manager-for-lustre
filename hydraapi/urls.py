# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

# django-piston handlers imports.
from django.conf.urls.defaults import patterns
from piston.resource import Resource

# Hydra server imports
from monitorapi import (ListFileSystems,
                        GetFileSystem,
                        GetFSTargets,
                        GetTargets,
                        GetMgtDetails,
                        #GetClients,
                        GetServers,
                        GetEventsByFilter,
                        GetLatestEvents,
                        GetAlerts,
                        GetJobs,
                        GetLogs,
                        GetFSVolumeDetails)

import configureapi
from configureapi import (FormatFileSystem,
                          StopFileSystem,
                          StartFileSystem,
                          AddHost,  
                          TestHost,
                          RemoveHost,
                          GetLuns,
                          CreateFilesystem,
                          CreateNewFilesystem,
                          CreateMGT,
                          CreateOSTs,
                          SetLNetStatus,
                          SetTargetMountStage,
                          GetJobStatus,
                          SetJobStatus,
                          Notifications)

# FIXME: instead of doing this big list of imports, should introspect available
# RequestHandler objects and get their url name from them.

# Stuff related to storage plugins
from configureapi import (GetResource,
                         GetResources,
                         GetResourceClasses,
                         SetResourceAlias,
                         GetTargetResourceGraph,
                         CreateStorageResource,
                         CreatableStorageResourceClasses,
                         StorageResourceClassFields)

#Once R3D starts getting correct data  replace fakestatsmetricapi with statmetricapi
from fakestatsmetricapi import(GetFSTargetStats_fake,
                           GetFSServerStats_fake,
                           GetServerStats_fake,
                           GetTargetStats_fake,
                           GetFSClientsStats_fake,
                           GetFSOSTHeatMap)  

from statsmetricapi import(GetFSTargetStats,
                           GetFSServerStats,
                           GetFSMGSStats,
                           GetServerStats,
                           GetTargetStats,
                           GetFSClientsStats,
                           GetHeatMapFSStats,
                           GetHeatMapServerStats)

from audit import HydraAudit,ClearAudit

# Cross Site Referance related class 
class CsrfExemptResource(Resource):
    """A Custom Resource that is csrf exempt"""
    def __init__(self, handler, authentication=None):
        super(CsrfExemptResource, self).__init__(handler, authentication)
        self.csrf_exempt = getattr(self.handler, 'csrf_exempt', True)

# hydra api urls definitions.
urlpatterns = patterns('',
    (r'^listfilesystems/$',CsrfExemptResource(ListFileSystems)),
    (r'^getfilesystem/$',CsrfExemptResource(GetFileSystem)),
    (r'^get_fs_targets/$',CsrfExemptResource(GetFSTargets)),
    (r'^get_targets/$',CsrfExemptResource(GetTargets)),
    (r'^get_mgts/$',CsrfExemptResource(GetMgtDetails)),
    (r'^getvolumesdetails/$',CsrfExemptResource(GetFSVolumeDetails)),
    (r'^listservers/$',CsrfExemptResource(GetServers)),
    #(r'^getclients/$',CsrfExemptResource(GetClients)),
    (r'^get_luns/$',CsrfExemptResource(GetLuns)),
    
    (r'^list_audit/$',CsrfExemptResource(HydraAudit)),
    (r'^clear_audit/$',CsrfExemptResource(ClearAudit)),
    
    (r'^format_filesystem/$',CsrfExemptResource(FormatFileSystem)), 
    (r'^stop_filesystem/$',CsrfExemptResource(StopFileSystem)), 
    (r'^start_filesystem/$',CsrfExemptResource(StartFileSystem)),
    (r'^create_new_fs/$',CsrfExemptResource(CreateNewFilesystem)),
    (r'^create_fs/$',CsrfExemptResource(CreateFilesystem)),
    (r'^create_mgt/$',CsrfExemptResource(CreateMGT)),
    (r'^create_osts/$',CsrfExemptResource(CreateOSTs)),  
    (r'^test_host/$',CsrfExemptResource(TestHost)),
    (r'^add_host/$',CsrfExemptResource(AddHost)),
    (r'^remove_host/$',CsrfExemptResource(RemoveHost)),
    (r'^set_lnet_state/$',CsrfExemptResource(SetLNetStatus)),
    (r'^set_target_stage/$',CsrfExemptResource(SetTargetMountStage)),
    (r'^get_job_status/$',CsrfExemptResource(GetJobStatus)),
    (r'^set_job_status/$',CsrfExemptResource(SetJobStatus)), 

    (r'^get_fs_stats_for_targets_fake/$',CsrfExemptResource(GetFSTargetStats_fake)),
    (r'^get_fs_stats_for_server_fake/$',CsrfExemptResource(GetFSServerStats_fake)),
    (r'^get_stats_for_server_fake/$',CsrfExemptResource(GetServerStats_fake)),
    (r'^get_stats_for_targets_fake/$',CsrfExemptResource(GetTargetStats_fake)),
    (r'^get_fs_stats_for_client_fake/$',CsrfExemptResource(GetFSClientsStats_fake)),
    (r'^get_fs_ost_heatmap_fake/$',CsrfExemptResource(GetFSOSTHeatMap)),

    (r'^get_fs_stats_for_targets/$',CsrfExemptResource(GetFSTargetStats)),
    (r'^get_fs_stats_for_server/$',CsrfExemptResource(GetFSServerStats)),
    (r'^get_fs_stats_for_mgs/$',CsrfExemptResource(GetFSMGSStats)),
    (r'^get_stats_for_server/$',CsrfExemptResource(GetServerStats)),
    (r'^get_stats_for_targets/$',CsrfExemptResource(GetTargetStats)),
    (r'^get_fs_stats_for_client/$',CsrfExemptResource(GetFSClientsStats)),
    (r'^get_fs_stats_heatmap/$',CsrfExemptResource(GetHeatMapFSStats)),
    (r'^get_server_stats_heatmap/$',CsrfExemptResource(GetHeatMapServerStats)),

    (r'^target/$',CsrfExemptResource(configureapi.Target)),

    (r'^geteventsbyfilter/$',CsrfExemptResource(GetEventsByFilter)),
    (r'^getlatestevents/$',CsrfExemptResource(GetLatestEvents)),
    (r'^getalerts/$',CsrfExemptResource(GetAlerts)),
    (r'^getjobs/$',CsrfExemptResource(GetJobs)),
    (r'^getlogs/$',CsrfExemptResource(GetLogs)),
    (r'^notifications/$',CsrfExemptResource(Notifications)),

    (r'^get_resource_classes/$', CsrfExemptResource(GetResourceClasses)),
    (r'^get_resources/$', CsrfExemptResource(GetResources)),
    (r'^get_resource/$', CsrfExemptResource(GetResource)),
    (r'^set_resource_alias/$', CsrfExemptResource(SetResourceAlias)),
    (r'^get_target_resource_graph/$', CsrfExemptResource(GetTargetResourceGraph)),

    (r'^storage_resource/$', CsrfExemptResource(CreateStorageResource)),
    (r'^storage_resource_class_fields/$', CsrfExemptResource(StorageResourceClassFields)),
    (r'^creatable_storage_resource_classes/$', CsrfExemptResource(CreatableStorageResourceClasses)),
)
