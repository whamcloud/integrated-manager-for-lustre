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
from monitor.models import SshMonitor
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
    @extract_exception
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
    @extract_exception
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


class TestHost(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.test_host)

    @classmethod
    @extract_request_args(host_name='hostname')
    @extract_exception
    def test_host(self,request,host_name):
        from monitor.tasks import test_host_contact
        host, ssh_monitor = SshMonitor.from_string(host_name)
        return test_host_contact(host,ssh_monitor)


class AddHost(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.add_host)

    @classmethod
    @extract_request_args(host_name='hostname')
    @extract_exception
    def add_host(self,request,host_name):
        host, ssh_monitor =SshMonitor.from_string(host_name)
        host.save()
        ssh_monitor.host = host
        ssh_monitor.save
        return {
                'host':host_name,
                'status': 'added'
               }

class RemoveHost(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.remove_host)

    @classmethod
    @extract_request_args(host_id='hostid')
    @extract_exception
    def remove_host(self,request,host_id):
        host =  ManagedHost.objects.get(id = host_id)
        StateManager.set_state(host,'removed')
        return {    
                'hostid': host_id,
                'status': 'RemoveHostJob submitted Job Id:'
               }

class SetLNetStatus(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.set_lnet_status)

    @classmethod
    @extract_request_args(host_id='hostid',state_string='state')
    @extract_exception
    def set_lnet_status(self,request,host_id,state_string):
        host =  ManagedHost.objects.get(id = host_id)
        StateManager.set_state(host,state_string)
        return {
                'hostid': host_id,
                'status': 'RemoveHostJob submitted Job Id:'
               }



class RemoveFileSystem(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.remove_filesystem)

    @classmethod
    @extract_request_args(filesystem_id='filesystemid')
    @extract_exception
    def remove_filesystem(self,request,filesystem_id):
        from configure.models import ManagedFilesystem
        from configure.models.state_manager import StateManager
        fs = ManagedFilesystem.objects.get(id = filesystem_id)    
        StateManager.set_state(fs,'removed')
        return {
                'filesystemid': filesystem_id,
                'status': 'RemoveFilesystemJob submitted Job Id:'
               }

class RemoveClient(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.remove_client)

    @classmethod
    @extract_request_args(client_id='clientid')
    @extract_exception
    def remove_client(self,request,client_id):
        from configure.models import ManagedTargetMount
        from configure.models.state_manager import StateManager
        mtm = ManagedTargetMount.objects.get(id = client_id)
        StateManager.set_state(mtm,'removed')
        return {
                'clientid': client_id,
                'status': 'RemoveManagedTargetJob submitted Job Id:'
               }

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
        from configure.models import ManagedFilesystem
        fs = ManagedFilesystem(mgs=mgs_name,name = filesystem_name)
        fs.save()

class CreateMGS(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.create_mgs)

    @classmethod
    @extract_request_args(host_id='hostid',node_id='nodeid',failover_id='failoverid')
    @extract_exception
    def create_mgs(self,request,host_id,node_id,failover_id):
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

    @classmethod
    @extract_exception
    def _create_target_mounts(self,node, target, failover_host = None):
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

    @classmethod
    @extract_exception
    def _set_target_states(self,targets, mounts):
        from configure.lib.state_manager import StateManager
        for target in targets:
            StateManager.set_state(target, 'mounted')
        for target in targets:
            StateManager.set_state(target, 'unmounted')
        for target in targets:
            StateManager.set_state(target, 'formatted')

class CreateOSS(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.create_oss)

    @classmethod
    @extract_request_args(host_id='hostid',node_id='nodeid',failover_id='failoverid',filesystem_id='filesystemid')
    @extract_exception
    def create_oss(self,request,host_id,node_id,failover_id,filesystem_id):
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

    @classmethod
    @extract_exception
    def _create_target_mounts(self,node, target, failover_host = None):
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

    @classmethod
    @extract_exception
    def _set_target_states(self,targets, mounts):
        from configure.lib.state_manager import StateManager
        for target in targets:
            StateManager.set_state(target, 'mounted')
        for target in targets:
            StateManager.set_state(target, 'unmounted')
        for target in targets:
            StateManager.set_state(target, 'formatted')


class CreateMDS(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.create_mds)

    @classmethod
    @extract_request_args(host_id='hostid',node_id='nodeid',failover_id='failoverid',filesystem_id='filesystemid')
    @extract_exception
    def create_mds(self,request,host_id,node_id,failover_id,filesystem_id):
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

    @classmethod
    @extract_exception
    def _create_target_mounts(self,node, target, failover_host = None):
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

    @classmethod
    @extract_exception
    def _set_target_states(self,targets, mounts):
        from configure.lib.state_manager import StateManager
        for target in targets:
            StateManager.set_state(target, 'mounted')
        for target in targets:
            StateManager.set_state(target, 'unmounted')
        for target in targets:
            StateManager.set_state(target, 'formatted')

