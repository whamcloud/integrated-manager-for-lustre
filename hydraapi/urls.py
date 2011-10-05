# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

# django-piston handlers imports.
from django.conf.urls.defaults import *
from piston.resource import Resource

# Hydra server imports
from monitorapi import (ListFileSystems,
                        GetFileSystem,
                        GetVolumes,
                        GetClients,
                        GetServers,
                        AddHost,
                        GetFSDiskUsage,
                        GetFSInodesUsage,
                        GetServerCPUUsage,
                        GetServerMemoryUsage,
                        GetTargetReads,
                        GetTargetWrites,
                        GetEventsByFilter,
                        GetLatestEvents,
                        GetAlerts,
                        GetJobs)

from configureapi import (FormatFileSystem,
                          StopFileSystem,
                          StartFileSystem,
                          RemoveHost,
                          GetAvailableDevices,
                          CreateFilesystem,
                          CreateMGS,
                          CreateOSS,
                          CreateMDS)

from audit import HydraAudit

# Cross Site Referance related class 
class CsrfExemptResource(Resource):
    """A Custom Resource that is csrf exempt"""
    def __init__(self, handler, authentication=None):
        super(CsrfExemptResource, self).__init__(handler, authentication)
        self.csrf_exempt = getattr(self.handler, 'csrf_exempt', True)

# django-piston resource mapping.
list_filesystems = CsrfExemptResource(ListFileSystems)
get_filesystem = CsrfExemptResource(GetFileSystem)
list_servers = CsrfExemptResource(GetServers)
get_clients = CsrfExemptResource(GetClients)
get_volumes = CsrfExemptResource(GetVolumes)

format_filesystem = CsrfExemptResource(FormatFileSystem)
stop_filesystem = CsrfExemptResource(StopFileSystem)
start_filesystem = CsrfExemptResource(StartFileSystem)
create_filesystem = CsrfExemptResource(CreateFilesystem)
create_mgs = CsrfExemptResource(CreateMGS)
create_oss = CsrfExemptResource(CreateOSS)
create_mds = CsrfExemptResource(CreateMDS)
add_host = CsrfExemptResource(AddHost)
remove_host = CsrfExemptResource(RemoveHost)

list_audit = CsrfExemptResource(HydraAudit)
clear_audit = CsrfExemptResource(HydraAudit)

get_fs_diskusage = CsrfExemptResource(GetFSDiskUsage)
get_fs_inodeusage = CsrfExemptResource(GetFSInodesUsage)
get_server_cpuusage = CsrfExemptResource(GetServerCPUUsage)
get_server_memoryusage = CsrfExemptResource(GetServerMemoryUsage)
get_target_reads = CsrfExemptResource(GetTargetReads)
get_target_writes = CsrfExemptResource(GetTargetWrites)

get_events_by_filter = CsrfExemptResource(GetEventsByFilter)
get_latest_events = CsrfExemptResource(GetLatestEvents)
get_alerts = CsrfExemptResource(GetAlerts)
get_jobs = CsrfExemptResource(GetJobs)

get_available_devices = CsrfExemptResource(GetAvailableDevices)

# hydra api urls definitions.
urlpatterns = patterns('',
    (r'^listfilesystems/$', list_filesystems),
    (r'^getfilesystem/$',get_filesystem),
    (r'^getvolumes/$',get_volumes),
    (r'^listservers/$',list_servers),
    (r'^getclients/$',get_clients),
    
    (r'^listaudit/$',list_audit),
    (r'^clearaudit/$',clear_audit),

    (r'^addhost/$',add_host),
    (r'^removehost/$',remove_host),
    
    (r'^formatfilesystem/$',format_filesystem), 
    (r'^stopfilesystem/$',stop_filesystem), 
    (r'^startfilesystem/$',start_filesystem),
    (r'^createfs/$',create_filesystem),
    (r'^createmgt/$',create_mgs),
    (r'^createost/$',create_oss),
    (r'^createmdt/$',create_mds),
    
    (r'^getfsdiskusage/$',get_fs_diskusage),
    (r'^getfsinodeusage/$',get_fs_inodeusage),
    (r'^getservercpuusage/$',get_server_cpuusage),
    (r'^getservermemoryusage/$',get_server_memoryusage),
    (r'^gettargetreads/$',get_target_reads),
    (r'^gettargetwrites/$',get_target_writes),

    (r'^geteventsbyfilter/$',get_events_by_filter),
    (r'^getlatestevents/$',get_latest_events),
    (r'^getalerts/$',get_alerts),
    (r'^getjobs/$',get_jobs),
    
    (r'^getdevices/$',get_available_devices),
)
