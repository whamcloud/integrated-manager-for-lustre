#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
#REST API Controller for Lustre File systems resource in configure namespace
from django.core.management import setup_environ

# Hydra server imports
import settings
setup_environ(settings)

from configure.models import (ManagedFilesystem,
                              ManagedHost,
                              ManagedMgs,
                              ManagedMdt,
                              ManagedOst)
from configure.lib.state_manager import (StateManager)
from requesthandler import (AnonymousRequestHandler,
                            extract_request_args)
#
class FormatFileSystem(AnonymousRequestHandler):
    
    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.format_filesystem)
    
    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    def format_filesystem(self,request,filesystem_name):
        format_fs_list = []
        fs = ManagedFilesystem.objects.get(name =  filesystem_name) 
        for target in fs.get_targets():
            if target.state == 'unformatted':
                StateManager.set_stage(target,'formatted')
                format_fs_list.append(
                                  { 
                                   'filesystem': fs.name,
                                   'target':target.name,
                                   'format_status': 'formatting...'   
                                  }
                )
            else:
                format_fs_list.append(
                                  {
                                   'filesystem': fs.name,
                                   'target':target.name,
                                   'format_status':'formatted' 
                                  } 
                )
        return format_fs_list
    
class StopFileSystem(AnonymousRequestHandler):
    
    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.stop_filesystem)
    
    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    def stop_filesystem(self,request,filesystem_name):
        format_fs_list = []
        fs = ManagedFilesystem.objects.get(name =  filesystem_name)
        for target in fs.get_targets():
            if not target.state == 'unmounted':
                StateManager.set_stage(target.downcast(),'unmounted')
                format_fs_list.append(
                                  {
                                   'filesystem': fs.name,
                                   'target':target.name,
                                   'format_status': 'unmountting'
                                  }
                )
            else:
                format_fs_list.append(
                                  {
                                   'filesystem': fs.name,
                                   'target':target.name,
                                   'format_status':'unmounted'
                                  }
                )
        return format_fs_list


class StartFileSystem(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.start_filesystem)

    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    def start_filesystem(self,request,filesystem_name):
        format_fs_list = []
        fs = ManagedFilesystem.objects.get(name =  filesystem_name)
        for target in fs.get_targets():
            StateManager.set_stage(target.downcast(),'mounted')
            format_fs_list.append(
                              {
                               'filesystem': fs.name,
                               'target':target.name,
                               'format_status': 'mountting'
                              }
            )
        return format_fs_list

class RemoveHost(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.remove_host)

    @classmethod
    @extract_request_args(host_id='hostid')
    def remove_host(self,request,host_id):
        try: 
            host =  ManagedHost.objects.get(id = host_id)
            StateManager.set_state(host,'removed')
            return {    
                    'hostid': host_id,
                    'status': 'RemoveHostJob submitted Job Id:'
                   }
        except:
            raise Exception ('Unable to remove host with id %s ' % host_id) 
 

class RemoveFileSystem(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.remove_filesystem)

    @classmethod
    @extract_request_args(filesystem_id='filesystemid')
    def remove_filesystem(self,request,filesystem_id):
        try:
            from configure.models import ManagedFilesystem
            from configure.models.state_manager import StateManager
            fs = ManagedFilesystem.objects.get(id = filesystem_id)    
            StateManager.set_state(fs,'removed')
            return {
                    'filesystemid': filesystem_id,
                    'status': 'RemoveFilesystemJob submitted Job Id:'
                   }
        except:
            raise Exception('Unable to remove filesystem with id %s' % filesystem_id) 


class RemoveClient(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.remove_client)

    @classmethod
    @extract_request_args(client_id='clientid')
    def remove_client(self,request,client_id):
        try:
            from configure.models import ManagedTargetMount
            from configure.models.state_manager import StateManager
            mtm = ManagedTargetMount.objects.get(id = client_id)
            StateManager.set_state(mtm,'removed')
            return {
                    'clientid': client_id,
                    'status': 'RemoveManagedTargetJob submitted Job Id:'
                   }
        except:
            raise Exception('Unable to remove client with id %s' % client_id)

class ListManagedFileSystems(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.list_managedfilesystems)

    @classmethod
    def list_managedfilesystems(self,request):
        return [
            {
                'id' : managedfilesystem.id,
                'name': managedfilesystem.name,
                'status' : managedfilesystem.status_string()
            }
            for managedfilesystem in ManagedFilesystem.objects.all()
        ]
     
class ListManagedHosts(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.list_managedhosts)

    @classmethod
    def list_managedhosts(self,request):
        return [
            {
                'id' : managedhost.id,
                'name': managedhost.name,
                'status' : managedhost.status_string()
            }
            for managedhost in ManagedHost.objects.all()
        ]

class ListManagedMgs(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.list_managedmgs)

    @classmethod
    def list_managedmgs(self,request):
        return [
            {
                'id' : managedmgs.id,
                'name': managedmgs.name,
                'status' : managedmgs.status_string()
            }
            for managedmgs in ManagedMgs.objects.all()
        ]

class ListManagedMdt(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.list_managedmdt)

    @classmethod
    def list_managedmdt(self,request):
        return [
            {
                'id' : managedmdt.id,
                'name': managedmdt.name,
                'status' : managedmdt.status_string()
            }
            for managedmdt in ManagedMdt.objects.all()
        ]

class ListManagedOst(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.list_managedost)

    @classmethod
    def list_managedost(self,request):
        return [
            {
                'id' : managedost.id,
                'name': managedost.name,
                'status' : managedost.status_string()
            }
            for managedost in ManagedOst.objects.all()
        ]




class GetManagedFSConfParams(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_managed_fs_conf_param)

    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    def get_managed_fs_conf_param(self,request,filesystem_name):
        managedfilesystem = ManagedFilesystem.objects.get(name = filesystem_name)
        confparam_list = managedfilesystem.get_conf_params(managedfilesystem)
        return [
            {
                'id' : managedfilesystem.id,
                'name': managedfilesystem.name,
                'status' : managedfilesystem.status_string()
            }
            for confparam in confparam_list
        ]
