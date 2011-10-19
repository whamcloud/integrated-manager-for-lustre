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

class GetResourceClasses(AnonymousRequestHandler):
    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_resource_classes)

    @classmethod
    @extract_request_args()
    @extract_exception
    def get_resource_classes(self, request):
        from configure.models import StorageResourceClass, StorageResourceRecord

        # Pick the first resource with no parents, and use its class
        try:
            default_resource = StorageResourceRecord.objects.filter(parents = None).latest('pk').resource_class
        except StorageResourceRecord.DoesNotExist:
            try:
                default_resource = StorageResourceRecord.objects.all()[0]
            except IndexError:
                default_resource = StorageResourceClass.objects.all()[0]

        def natural_id(src):
            """Since resource classes are uniquely identified internally by module name
            plus class name, we don't have to use the PK."""
            return (src.storage_plugin.module_name, src.class_name)
        def label(src):
            return "%s-%s" % (src.storage_plugin.module_name, src.class_name)
        return {
                'options': [(natural_id(src), label(src)) for src in StorageResourceClass.objects.all()],
                'default': natural_id(default_resource)
                }

class GetResources(AnonymousRequestHandler):
    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_resources)

    @classmethod
    @extract_request_args(module_name='module_name', class_name='class_name')
    @extract_exception
    def get_resources(self, request, module_name, class_name):
        from configure.lib.storage_plugin.manager import storage_plugin_manager
        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(module_name, class_name)
        attr_columns = resource_class.get_columns()
        columns = ['id', 'alias'] + attr_columns

        rows = []
        from django.utils.html import conditional_escape
        from configure.lib.storage_plugin.query import ResourceQuery
        for record in ResourceQuery().get_class_resources(resource_class_id):
            resource = record.to_resource()
            alias = record.alias_or_name(resource)

            # NB What we output here is logically markup, not strings, so we escape.
            # (underlying storage_plugin.attributes do their own escaping
            row = [record.pk, conditional_escape(alias)]
            row = row + [resource.format(c) for c in attr_columns]
                
            rows.append(row)    
        datatables_columns = [{'sTitle': c} for c in columns]
        return {'aaData': rows, 'aoColumns': datatables_columns}

# FIXME: this should be part of /storage_resource/
# FIXME: should return a 204 status code
class SetResourceAlias(AnonymousRequestHandler):
    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.set_resource_alias)

    @classmethod
    @extract_request_args(resource_id='resource_id', alias='alias')
    @extract_exception
    def set_resource_alias(cls, request, resource_id, alias):
        from configure.models import StorageResourceRecord
        from django.shortcuts import get_object_or_404
        record = get_object_or_404(StorageResourceRecord, id = resource_id)
        if alias == "":
            record.alias = None
        else:
            record.alias = alias
        record.save()
        return {}

class GetResource(AnonymousRequestHandler):
    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_resource)

    @classmethod
    @extract_request_args(resource_id='resource_id')
    @extract_exception
    def get_resource(cls, request, resource_id):
        from configure.models import StorageResourceRecord
        from django.shortcuts import get_object_or_404
        record = get_object_or_404(StorageResourceRecord, id = resource_id)
        resource = record.to_resource()

        from configure.lib.storage_plugin.query import ResourceQuery
        alerts = [a.to_dict() for a in ResourceQuery().resource_get_alerts(resource)]
        prop_alerts = [a.to_dict() for a in ResourceQuery().resource_get_propagated_alerts(resource)]

        from configure.models import StorageResourceStatistic
        stats = {}
        for s in StorageResourceStatistic.objects.filter(storage_resource = resource_id):
            stats[s.name] = s.to_dict()

        attributes = resource.attr_dict()
        return {'alias': record.alias,
                'default_alias': record.to_resource().human_string(),
                'attributes': attributes,
                'alerts': alerts,
                'stats': stats,
                'propagated_alerts': prop_alerts}

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

