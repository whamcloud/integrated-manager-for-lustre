#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
# REST API Conrtoller for Lustre File systems resource monitor name space
from django.core.management import setup_environ

# Hydra server imports
import settings
setup_environ(settings)

from requesthandler import (AnonymousRequestHandler,
                            extract_request_args)
from monitor.models import (Filesystem,
                            MetadataTarget,
                            ManagementTarget,
                            ObjectStoreTarget,
                            Client,
                            Host,
                            SshMonitor)

# Logger Settings
import logging
hydraapi_log = logging.getLogger('hydraapi')
hydraapi_log.setLevel(logging.DEBUG)
handler = logging.FileHandler(settings.API_LOG_PATH)
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
hydraapi_log.addHandler(handler)
if settings.DEBUG:
    hydraapi_log.setLevel(logging.DEBUG)
    hydraapi_log.addHandler(logging.StreamHandler())
else:
    hydraapi_log.setLevel(logging.INFO)

#
class ListFileSystems(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.list_filesystems)

    @classmethod
    def list_filesystems(self,request):
        return [
            {
                'id' : filesystem.id,
                'name': filesystem.name,
                'status' : filesystem.status_string()
            } 
            for filesystem in Filesystem.objects.all()
        ]

class GetFileSystem(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_filesystem)

    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    def get_filesystem(self,request,filesystem_name):
        if filesystem_name:
            filesystem = Filesystem.objects.get(name = filesystem_name)
            return {             
                'id' : filesystem.id,
                'name': filesystem.name,
                'status' : filesystem.status_string()
            }            

class GetVolumes(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
       AnonymousRequestHandler.__init__(self,self.get_volumes)

    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    def get_volumes(self,request,filesystem_name):
        if filesystem_name:
            return self.get_volumes_per_fs(Filesystem.objects.get(name = filesystem_name))
        else:
            volumes_list = []
            for fs in Filesystem.objects.all():
                volumes_list.extend(self.get_volumes_per_fs(fs.name))
            return volumes_list

    @classmethod
    def get_volumes_per_fs (self,filesystem_name):
        volume_list = []
        filesystem = Filesystem.objects.get(name = filesystem_name)
        volume_list.append(
                        {
                            'id' : filesystem.id,
                            'name': filesystem.name,
                            #'kind': filesystem.role(),
                            'status' : filesystem.status_string()
                        }
         )

        try:
            volume_list.append(
                            {
                                'id' : filesystem.mgs.id,
                                'name': filesystem.mgs.name,
                                'kind': filesystem.mgs.role(),
                                'status' : filesystem.mgs.status_string()
                            }
            )
        except ManagementTarget.DoesNotExist:
            pass
        try:
            mdt = MetadataTarget.objects.get (filesystem = filesystem)
            volume_list.append(
                            {
                                'id' : mdt.id,
                                'name': mdt.name,
                                'kind': mdt.role(),
                                'status' : mdt.status_string()
                            }
            )            
        except MetadataTarget.DoesNotExist:
             pass
        osts = ObjectStoreTarget.objects.filter(filesystem = filesystem)
        volume_list.extend([
                        {
                            'id' : ost.id,
                            'name': ost.name,
                            'kind': ost.role(),
                            'status' : ost.status_string()
                         }  
                         for ost in osts
                        ])

        return volume_list  

class GetClients (AnonymousRequestHandler):
         
    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_clients)

    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    def get_clients(self,request,filesystem_name):
        if filesystem_name :
            return self.__get_clients(filesystem_name)
        else:
           client_list = []
           for filesystem in Filesystem.objects.all():
               client_list.extend(self.__get_clients(filesystem.name))
        return client_list
                              
    @classmethod 
    def __get_clients(self,filesystem_name):
        fsname = Filesystem.objects.get(name = filesystem_name)
        return [
                 { 
                   'id' : client.id,
                   'host' : client.host.address,
                   'mount_point' : client.mount_point,
                   #'status' : self.__mountable_audit_status(client)
                 }      
                 for client in Client.objects.filter(filesystem = fsname)
        ]

class GetServers (AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.list_servers)

    @classmethod
    def list_servers(self,request):
        return [
             { 
               'id' : host.id,
               'host_address' : host.address,
               'kind' : host.role() ,
               'lnet_status' : host.status_string()
             }
             for host in Host.objects.all()
         ]

class AddHost(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.add_host)

    @classmethod
    @extract_request_args(host_name='hostname')
    def add_host(self,request,host_name):
        try:
            host, ssh_monitor =SshMonitor.from_string(host_name)
            host.save()
            ssh_monitor.host = host
            ssh_monitor.save
            return {
                    'host':host_name,
                    'status': 'added'
                   }
        except:
            raise Exception('Unable to add Host: %s' % host_name)   
