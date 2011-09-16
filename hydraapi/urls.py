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
                         AddHost) 

from configureapi import (FormatFileSystem,
                          StopFileSystem,
                          StartFileSystem,
                          RemoveHost)

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
format_filesystem = CsrfExemptResource(FormatFileSystem)
stop_filesystem = CsrfExemptResource(StopFileSystem)
start_filesystem = CsrfExemptResource(StartFileSystem)
get_volumes = CsrfExemptResource(GetVolumes)
list_servers = CsrfExemptResource(GetServers)
add_host = CsrfExemptResource(AddHost)
remove_host = CsrfExemptResource(RemoveHost)
get_clients = CsrfExemptResource(GetClients)
list_audit = CsrfExemptResource(HydraAudit)
clear_audit = CsrfExemptResource(HydraAudit)

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
)
