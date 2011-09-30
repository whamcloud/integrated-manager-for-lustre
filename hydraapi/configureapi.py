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
                              ManagedHost)
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
        try:
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
        except:
            raise Exception('POST call API_Exception:format_filesystem(filesystem_name) => Failed to format filesystem=%s' %filesystem_name)
    
class StopFileSystem(AnonymousRequestHandler):
    
    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.stop_filesystem)
    
    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    def stop_filesystem(self,request,filesystem_name):
        try:    
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
        except:
            raise Exception('POST call API_Exception:stop_filesystem(filesystem_name) => Failed to stop the filesystem=%s' %filesystem_name)

class StartFileSystem(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.start_filesystem)

    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    def start_filesystem(self,request,filesystem_name):
        try:
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
        except:
            raise Exception('POST call API_Exception:start_filesystem(filesystem_name) => Failed to start the filesystem=%s' %filesystem_name)

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
            raise Exception ('POST call API_Exception:remove_host(host_id) => Failed to remove the host with hostid=%s' % host_id) 
 

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
            raise Exception('POST call API_Exception:remove_filesystem(filesystem_id) => Failed to remove the filesystem with filesystemid=%s' % filesystem_id) 


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
            raise Exception('POST call API_Exception:remove_client(client_id) => Failed to remove the client with clientid=%s' % client_id)

