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
                            extract_request_args,
                            extract_exception)
#
class FormatFileSystem(AnonymousRequestHandler):
    
    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.format_filesystem)
    
    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    @extract_exception
    def format_filesystem(self,request,filesystem_name):
        #try:
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
        #except:
        #    raise Exception('POST call API_Exception:format_filesystem(filesystem_name) => Failed to format filesystem=%s' %filesystem_name)
    
class StopFileSystem(AnonymousRequestHandler):
    
    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.stop_filesystem)
    
    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    @extract_exception
    def stop_filesystem(self,request,filesystem_name):
        #try:    
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
        #except:
        #    raise Exception('POST call API_Exception:stop_filesystem(filesystem_name) => Failed to stop the filesystem=%s' %filesystem_name)

class StartFileSystem(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.start_filesystem)

    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    @extract_exception
    def start_filesystem(self,request,filesystem_name):
        #try:
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
        #except:
        #    raise Exception('POST call API_Exception:start_filesystem(filesystem_name) => Failed to start the filesystem=%s' %filesystem_name)

class RemoveHost(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.remove_host)

    @classmethod
    @extract_request_args(host_id='hostid')
    @extract_exception
    def remove_host(self,request,host_id):
        #try: 
            host =  ManagedHost.objects.get(id = host_id)
            StateManager.set_state(host,'removed')
            return {    
                    'hostid': host_id,
                    'status': 'RemoveHostJob submitted Job Id:'
                   }
        #except:
        #    raise Exception ('POST call API_Exception:remove_host(host_id) => Failed to remove the host with hostid=%s' % host_id) 
 

class RemoveFileSystem(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.remove_filesystem)

    @classmethod
    @extract_request_args(filesystem_id='filesystemid')
    @extract_exception
    def remove_filesystem(self,request,filesystem_id):
        #try:
            from configure.models import ManagedFilesystem
            from configure.models.state_manager import StateManager
            fs = ManagedFilesystem.objects.get(id = filesystem_id)    
            StateManager.set_state(fs,'removed')
            return {
                    'filesystemid': filesystem_id,
                    'status': 'RemoveFilesystemJob submitted Job Id:'
                   }
        #except:
        #    raise Exception('POST call API_Exception:remove_filesystem(filesystem_id) => Failed to remove the filesystem with filesystemid=%s' % filesystem_id) 


class RemoveClient(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.remove_client)

    @classmethod
    @extract_request_args(client_id='clientid')
    @extract_exception
    def remove_client(self,request,client_id):
        #try:
            from configure.models import ManagedTargetMount
            from configure.models.state_manager import StateManager
            mtm = ManagedTargetMount.objects.get(id = client_id)
            StateManager.set_state(mtm,'removed')
            return {
                    'clientid': client_id,
                    'status': 'RemoveManagedTargetJob submitted Job Id:'
                   }
        #except:
        #    raise Exception('POST call API_Exception:remove_client(client_id) => Failed to remove the client with clientid=%s' % client_id)

class GetLuns(AnonymousRequestHandler):
    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_luns)

    @classmethod
    @extract_request_args(category='category')
    @extract_exception
    def get_luns(cls,request, category):
        assert category in ['unused', 'usable']

        from monitor.models import Lun, LunNode
        from monitor.lib.util import sizeof_fmt
        devices = []
        if category == 'unused':
            luns = Lun.get_unused_luns()
        elif category == 'usable':
            luns = Lun.get_usable_luns()
        else:
            raise RuntimeError("Bad category '%s' in get_unused_luns" % category)

        for lun in luns:
            available_hosts = dict([(ln.host.id, {
                'label': ln.host.__str__(),
                'use': ln.use,
                'primary': ln.primary
                }) for ln in LunNode.objects.filter(lun = lun)])
            devices.append({
                             'id': lun.id,
                             'name': lun.human_name(),
                             'kind': lun.human_kind(),
                             'available_hosts': available_hosts,
                             'size':sizeof_fmt(lun.size),
                             'status': lun.ha_status()
                           })
        return devices

class CreateFilesystem(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.create_filesystem)

    @classmethod
    @extract_request_args(mgs_name='mgs',filesystem_name='fsname')
    @extract_exception
    def create_filesystem(self,request,mgs_name,filesystem_name):
        #try:
            from configure.models import ManagedFilesystem
            fs = ManagedFilesystem(mgs=mgs_name,name = filesystem_name)
            fs.save()
        #except:
        #    raise Exception('POST call API_Exception:create_filesystem(mgs_name,filesystem_name) => Failed to create filesystem with mgs=%s fsname=%s' % mgs_name %filesystem_name)

class CreateMGS(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.create_mgs)

    @classmethod
    @extract_request_args(host_id='hostid',node_id='nodeid',failover_id='failoverid')
    @extract_exception
    def create_mgs(self,request,host_id,node_id,failover_id):
        #try:
            from monitor.models import Host
            from monitor.models import LunNode
            from configure.models import ManagedMgs 
            from django.db import transaction
            #host = Host.objects.get(id=host_id) 
            node = LunNode.objects.get(id=node_id)
            failover_host = Host.objects.get(id=failover_id)
            target = ManagedMgs(name='MGS')
            target.save()
            mounts = self._create_target_mounts(node,target,failover_host)
            # Commit before spawning celery tasks
            transaction.commit()
            self._set_target_states([target], mounts)
        #except:
        #    raise Exception('POST call API_Exception: =>create_mgs(hostid,nodeid,failoverid) Failed to create MGS using hostid=%s nodeid=%s failoverid=%s' %host_id %node_id %failover_id)

    @classmethod
    @extract_exception
    def _create_target_mounts(self,node, target, failover_host = None):
        #try:
            from configure.models import ManagedTargetMount
            primary = ManagedTargetMount(
                block_device = node,
                target = target,
                host = node.host,
                mount_point = target.default_mount_path(node.host),
                primary = True)
            primary.save()
            if failover_host:
                failover = ManagedTargetMount(
                    block_device = None,
                    target = target,
                    host = failover_host,
                    mount_point = target.default_mount_path(failover_host),
                    primary = False)
                failover.save()
                return [primary, failover]

        #except:
        #    raise Exception('sub call API Exception=> _create_target_mounts(node,target,failover_host) failed to save created MGS')

    @classmethod
    @extract_exception
    def _set_target_states(self,targets, mounts):
        #try:
            from configure.lib.state_manager import StateManager
            for target in targets:
                StateManager.set_state(target, 'mounted')
            for target in targets:
                StateManager.set_state(target, 'unmounted')
            for target in targets:
                StateManager.set_state(target, 'formatted')
        #except:
        #    raise Exception('sub call API Exception=>_set_target_states(targets,mounts) Failed to set states for created MGS')

class CreateOSS(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.create_oss)

    @classmethod
    @extract_request_args(host_id='hostid',node_id='nodeid',failover_id='failoverid',filesystem_id='filesystemid')
    @extract_exception
    def create_oss(self,request,host_id,node_id,failover_id,filesystem_id):
        #try:
            from monitor.models import Host
            from monitor.models import LunNode
            from configure.models import ManagedOst
            from django.db import transaction
            #host = Host.objects.get(id=host_id)
            filesystem = ManagedFilesystem.objects.get(id=filesystem_id)
            node = LunNode.objects.get(id=node_id)
            failover_host = Host.objects.get(id=failover_id)
            target = ManagedOst(filesystem = filesystem)
            target.save()
            mounts = self._create_target_mounts(node,target,failover_host)
            # Commit before spawning celery tasks
            transaction.commit()
            self._set_target_states([target], mounts)
        #except:
        #    raise Exception('POST call API_Exception: =>create_oss(hostid,nodeid,failoverid,filesystemid) Failed to create OSS using hostid=%s nodeid=%s failoverid=%s filesystemid=%' %host_id %node_id %failover_id %filesystem_id)

    @classmethod
    @extract_exception
    def _create_target_mounts(self,node, target, failover_host = None):
        #try:
            from configure.models import ManagedTargetMount
            primary = ManagedTargetMount(
                block_device = node,
                target = target,
                host = node.host,
                mount_point = target.default_mount_path(node.host),
                primary = True)
            primary.save()
            if failover_host:
                failover = ManagedTargetMount(
                    block_device = None,
                    target = target,
                    host = failover_host,
                    mount_point = target.default_mount_path(failover_host),
                    primary = False)
                failover.save()
                return [primary, failover]
            else:
                return [primary]
        #except:
        #    raise Exception('sub call API Exception=> _create_target_mounts(node,target,failover_host) failed to save created OSS')

    @classmethod
    @extract_exception
    def _set_target_states(self,targets, mounts):
        #try:
            from configure.lib.state_manager import StateManager
            for target in targets:
                StateManager.set_state(target, 'mounted')
            for target in targets:
                StateManager.set_state(target, 'unmounted')
            for target in targets:
                StateManager.set_state(target, 'formatted')
        #except:
        #    raise Exception('sub call API Exception=>_set_target_states(targets,mounts) Failed to set states for created OSS')


class CreateMDS(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.create_mds)

    @classmethod
    @extract_request_args(host_id='hostid',node_id='nodeid',failover_id='failoverid',filesystem_id='filesystemid')
    @extract_exception
    def create_mds(self,request,host_id,node_id,failover_id,filesystem_id):
        #try:
            from monitor.models import Host
            from monitor.models import LunNode
            from configure.models import ManagedMdt
            from django.db import transaction
            #host = Host.objects.get(id=host_id)
            filesystem = ManagedFilesystem.objects.get(id=filesystem_id)
            node = LunNode.objects.get(id=node_id)
            failover_host = Host.objects.get(id=failover_id)
            target = ManagedMdt(filesystem = filesystem)
            target.save()
            mounts = self._create_target_mounts(node,target,failover_host)
            # Commit before spawning celery tasks
            transaction.commit()
            self._set_target_states([target], mounts)
        #except:
        #    raise Exception('POST call API_Exception: =>create_oss(hostid,nodeid,failoverid,filesystemid) Failed to create MDS using hostid=%s nodeid=%s failoverid=%s filesystemid=%' %host_id %node_id %failover_id %filesystem_id)

    @classmethod
    @extract_exception
    def _create_target_mounts(self,node, target, failover_host = None):
        #try:
            from configure.models import ManagedTargetMount
            primary = ManagedTargetMount(
                block_device = node,
                target = target,
                host = node.host,
                mount_point = target.default_mount_path(node.host),
                primary = True)
            primary.save()
            if failover_host:
                failover = ManagedTargetMount(
                    block_device = None,
                    target = target,
                    host = failover_host,
                    mount_point = target.default_mount_path(failover_host),
                    primary = False)
                failover.save()
                return [primary, failover]
            else:
                return [primary]
        #except:
        #    raise Exception('sub call API Exception=> _create_target_mounts(node,target,failover_host) failed to save created MDS')

    @classmethod
    @extract_exception
    def _set_target_states(self,targets, mounts):
        #try:
            from configure.lib.state_manager import StateManager
            for target in targets:
                StateManager.set_state(target, 'mounted')
            for target in targets:
                StateManager.set_state(target, 'unmounted')
            for target in targets:
                StateManager.set_state(target, 'formatted')
        #except:
        #    raise Exception('sub call API Exception=>_set_target_states(targets,mounts) Failed to set states for created MDS')

