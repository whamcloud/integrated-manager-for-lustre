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
    @extract_request_args('filesystem')
    def run(self,request,filesystem):
        format_fs_list = []
        fs = ManagedFilesystem.objects.get(name =  filesystem) 
        for target in fs.get_targets():
            if target.state == 'unformatted':
                StateManager.set_stage(target,'formatted')
                format_fs_list.append(
                                      { 
                                       'filesystem': fs.name,
                                       'target':target.name,
                                       'Job_id': ''   
                                       }
                                      )
            else:
                format_fs_list.append(
                                      {
                                       'filesystem': fs.name,
                                       'target':target.name,
                                       'Job_id':'' 
                                      } 
                                     )
        return format_fs_list
    
class StopFileSystem(AnonymousRequestHandler):
    @extract_request_args('filesystem')
    def run(self,request,filesystem):
        format_fs_list = []
        fs = ManagedFilesystem.objects.get(name =  filesystem)
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
    @extract_request_args('filesystem')
    def run(self,request,filesystem):
        format_fs_list = []
        fs = ManagedFilesystem.objects.get(name = filesystem)
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
    @extract_request_args('hostname')
    def run(self,request,hostname):
        from monitor.tasks import test_host_contact
        from configure.models import SshMonitor
        host, ssh_monitor = SshMonitor.from_string(hostname)
        job = test_host_contact.delay(host, ssh_monitor)
        return {'task_id': job.task_id}


class AddHost(AnonymousRequestHandler):
    @extract_request_args('hostname')
    def run(self,request,hostname):
        host = ManagedHost.create_from_string(hostname)
        return {
                'host': hostname,
                'status': 'added'
               }

class RemoveHost(AnonymousRequestHandler):
    @extract_request_args('hostid')
    def run(self,request,hostid):
        host =  ManagedHost.objects.get(id = hostid)
        StateManager.set_state(host,'removed')
        return {    
                'hostid': hostid,
                'status': 'RemoveHostJob submitted Job Id:'
               }

class SetLNetStatus(AnonymousRequestHandler):
    @extract_request_args('hostid','state')
    def run(self,request,hostid,state):
        host =  ManagedHost.objects.get(id = hostid)
        StateManager.set_state(host,state)
        return {
                'hostid': hostid,
                'status': 'RemoveHostJob submitted Job Id:'
               }

class RemoveFileSystem(AnonymousRequestHandler):
    @extract_request_args('filesystemid')
    def run(self,request,filesystemid):
        from configure.models import ManagedFilesystem
        from configure.models.state_manager import StateManager
        fs = ManagedFilesystem.objects.get(id = filesystemid)    
        StateManager.set_state(fs,'removed')
        return {
                'filesystemid': filesystemid,
                'status': 'RemoveFilesystemJob submitted Job Id:'
               }

class RemoveClient(AnonymousRequestHandler):
    @extract_request_args('clientid')
    def run(self,request,clientid):
        from configure.models import ManagedTargetMount
        from configure.models.state_manager import StateManager
        mtm = ManagedTargetMount.objects.get(id = clientid)
        StateManager.set_state(mtm,'removed')
        return {
                'clientid': clientid,
                'status': 'RemoveManagedTargetJob submitted Job Id:'
               }

class GetResourceClasses(AnonymousRequestHandler):
    def run(self, request):
        from configure.models import StorageResourceClass, StorageResourceRecord

        # Pick the first resource with no parents, and use its class
        try:
            default_resource = StorageResourceRecord.objects.filter(parents = None).latest('pk').resource_class
        except StorageResourceRecord.DoesNotExist:
            try:
                default_resource = StorageResourceRecord.objects.all()[0]
            except IndexError:
                try:
                    default_resource = StorageResourceClass.objects.all()[0]
                except IndexError:
                    raise RuntimeError('No storage resource classes')

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
    @extract_request_args('module_name','class_name')
    def run(self, request, module_name, class_name):
        from configure.lib.storage_plugin.manager import storage_plugin_manager
        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(module_name, class_name)
        attr_columns = resource_class.get_columns()
        columns = ['id', 'Name'] + attr_columns

        rows = []
        from django.utils.html import conditional_escape
        from configure.lib.storage_plugin.query import ResourceQuery
        for record in ResourceQuery().get_class_resources(resource_class_id):
            resource = record.to_resource()
            alias = conditional_escape(record.alias_or_name(resource))
            alias_markup = "<a class='storage_resource' href='#%s'>%s</a>" % (record.pk, alias)

            # NB What we output here is logically markup, not strings, so we escape.
            # (underlying storage_plugin.attributes do their own escaping
            row = [record.pk, alias_markup]
            row = row + [resource.format(c) for c in attr_columns]
                
            rows.append(row)    

        # FIXME: this is a workaround, forcing column widths because this is rendered in
        # an iframe inside jquery-ui tabs, so datatables can't calculate its width properly
        colpct = int(100.0 / len(columns))
        datatables_columns = [{'sTitle': c, 'sWidth': "%dpx" % colpct} for c in columns]
        return {'aaData': rows, 'aoColumns': datatables_columns}

# FIXME: this should be part of /storage_resource/
# FIXME: should return a 204 status code
class SetResourceAlias(AnonymousRequestHandler):
    @extract_request_args('resource_id','alias')
    def run(cls, request, resource_id, alias):
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
    @extract_request_args('resource_id')
    def run(cls, request, resource_id):
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
        return {'id': record.pk,
                'class_name': resource.human_class(),
                'alias': record.alias,
                'default_alias': record.to_resource().human_string(),
                'attributes': attributes,
                'alerts': alerts,
                'stats': stats,
                'propagated_alerts': prop_alerts}

class GetLuns(AnonymousRequestHandler):
    @extract_request_args('category')
    def run(cls,request, category):
        assert category in ['unused', 'usable']

        from configure.models import Lun, LunNode
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
    @extract_request_args('mgs','fsname')
    def run(self,request,mgs,fsname):
        from configure.models import ManagedFilesystem
        fs = ManagedFilesystem(mgs=mgs,name = fsname)
        fs.save()

class CreateMGS(AnonymousRequestHandler):
    @extract_request_args('hostid','nodeid','failoverid')
    def run(self,request,hostid,nodeid,failoverid):
        from configure.models import ManagedMgs, Host, LunNode
        from django.db import transaction
        #host = Host.objects.get(id=hostid) 
        node = LunNode.objects.get(id=nodeid)
        failover_host = ManagedHost.objects.get(id=failoverid)
        target = ManagedMgs(name='MGS')
        target.save()
        mounts = self._create_target_mounts(node,target,failover_host)
        # Commit before spawning celery tasks
        transaction.commit()
        self._set_target_states([target], mounts)

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

    def _set_target_states(self,targets, mounts):
        from configure.lib.state_manager import StateManager
        for target in targets:
            StateManager.set_state(target, 'mounted')
        for target in targets:
            StateManager.set_state(target, 'unmounted')
        for target in targets:
            StateManager.set_state(target, 'formatted')

class CreateOSS(AnonymousRequestHandler):
    @extract_request_args('hostid','nodeid','failoverid','filesystemid')
    def run(self,request,hostid,nodeid,failoverid,filesystemid):
        from configure.models import ManagedOst, ManagedHost, LunNode
        from django.db import transaction
        #host = Host.objects.get(id=hostid)
        filesystem = ManagedFilesystem.objects.get(id=filesystemid)
        node = LunNode.objects.get(id=nodeid)
        failover_host = ManagedHost.objects.get(id=failoverid)
        target = ManagedOst(filesystem = filesystem)
        target.save()
        mounts = self._create_target_mounts(node,target,failover_host)
        # Commit before spawning celery tasks
        transaction.commit()
        self._set_target_states([target], mounts)

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

    def _set_target_states(self,targets, mounts):
        from configure.lib.state_manager import StateManager
        for target in targets:
            StateManager.set_state(target, 'mounted')
        for target in targets:
            StateManager.set_state(target, 'unmounted')
        for target in targets:
            StateManager.set_state(target, 'formatted')


class CreateMDS(AnonymousRequestHandler):
    @extract_request_args('hostid','nodeid','failoverid','filesystemid')
    def run(self,request,hostid,nodeid,failoverid,filesystemid):
        from configure.models import ManagedMdt, ManagedHost, LunNode
        from django.db import transaction
        #host = Host.objects.get(id=hostid)
        filesystem = ManagedFilesystem.objects.get(id=filesystemid)
        node = LunNode.objects.get(id=nodeid)
        failover_host = ManagedHost.objects.get(id=failoverid)
        target = ManagedMdt(filesystem = filesystem)
        target.save()
        mounts = self._create_target_mounts(node,target,failover_host)
        # Commit before spawning celery tasks
        transaction.commit()
        self._set_target_states([target], mounts)

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

    def _set_target_states(self,targets, mounts):
        from configure.lib.state_manager import StateManager
        # FIXME: this is broken, you have miscopied the original from configure.views.
        # You don't have to tell the backend how to get between states, just tell it
        # what the eventual state should be.
        for target in targets:
            StateManager.set_state(target, 'mounted')
        for target in targets:
            StateManager.set_state(target, 'unmounted')
        for target in targets:
            StateManager.set_state(target, 'formatted')

class GetTargetResourceGraph(AnonymousRequestHandler):
    @extract_request_args('target_id')
    def run(self, request, target_id):
        from monitor.models import AlertState
        from configure.models import StorageResourceRecord, ManagedTarget
        from django.shortcuts import get_object_or_404
        if True:
            # FIXME HYD-375 HACK - the breadcrumb UI passes around names instead of ids, so have to do
            # this unreliable lookup instead
            target = get_object_or_404(ManagedTarget, name = target_id).downcast()
        else:
            target = get_object_or_404(ManagedTarget, pk = target_id).downcast()

        ancestor_records = set()
        parent_records = set()
        storage_alerts = set()
        lustre_alerts = set(AlertState.filter_by_item(target))
        from collections import defaultdict
        rows = defaultdict(list)
        id_edges = []
        for tm in target.managedtargetmount_set.all():
            lustre_alerts |= set(AlertState.filter_by_item(tm))
            lun_node = tm.block_device
            if lun_node.storage_resource:
                parent_record = lun_node.storage_resource
                from configure.lib.storage_plugin.query import ResourceQuery

                parent_records.add(parent_record)

                storage_alerts |= ResourceQuery().record_all_alerts(parent_record)
                ancestor_records |= set(ResourceQuery().record_all_ancestors(parent_record))

                def row_iterate(parent_record, i):
                    if not parent_record in rows[i]:
                        rows[i].append(parent_record)
                    for p in parent_record.parents.all():
                        #if 25 in [parent_record.id, p.id]:
                        #    id_edges.append((parent_record.id, p.id))
                        id_edges.append((parent_record.id, p.id))
                        row_iterate(p, i + 1)
                row_iterate(parent_record, 0)

        for i in range(0, len(rows) - 1):
            this_row = rows[i]
            next_row = rows[i + 1]
            def nextrow_affinity(obj):
                # if this has a link to anything in the next row, what
                # index in the next row?
                for j in range(0, len(next_row)):
                    notional_edge = (obj.id, next_row[j].id)
                    if notional_edge in id_edges:
                        return j
                return None

            this_row.sort(lambda a,b: cmp(nextrow_affinity(a), nextrow_affinity(b)))

        box_width = 120
        box_height = 80
        xborder = 40
        yborder = 40
        xpad = 20
        ypad = 20

        height = 0
        width = len(rows) * box_width + (len(rows) - 1) * xpad
        for i, items in rows.items():
            total_height = len(items) * box_height + (len(items) - 1) * ypad
            height = max(total_height, height)

        height = height + yborder * 2
        width = width + xborder * 2

        edges = [e for e in id_edges]
        nodes = []
        x = 0
        from settings import STATIC_URL
        for i, items in rows.items():
            total_height = len(items) * box_height + (len(items) - 1) * ypad
            y = (height - total_height) / 2 
            for record in items:
                resource = record.to_resource()
                alert_count = len(ResourceQuery().resource_get_alerts(resource))
                if alert_count != 0:
                    highlight = "#ff0000"
                else:
                    highlight = "#000000"
                nodes.append({
                    'left': x,
                    'top': y,
                    'title': record.alias_or_name(),
                    'icon': "%simages/storage_plugin/%s.png" % (STATIC_URL, resource.icon),
                    'type': resource.human_class(),
                    'id': record.id,
                    'highlight': highlight
                    })
                y += box_height + ypad
            x += box_width + xpad

        graph = {
                'edges': edges,
                'nodes': nodes,
                'item_width': box_width,
                'item_height': box_height,
                'width': width,
                'height': height
                }

        return {
            'storage_alerts': [a.to_dict() for a in storage_alerts],
            'lustre_alerts': [a.to_dict() for a in lustre_alerts],
            'graph': graph}

class CreateStorageResource(AnonymousRequestHandler):
    @extract_request_args('plugin', 'resource_class', 'attributes')
    def run(self, request, plugin, resource_class, attributes):
        from configure.lib.storage_plugin.manager import storage_plugin_manager
        storage_plugin_manager.create_root_resource(plugin, resource_class, **attributes)

class CreatableStorageResourceClasses(AnonymousRequestHandler):
    @extract_request_args()
    def run(self, request):
        from configure.lib.storage_plugin.manager import storage_plugin_manager
        return storage_plugin_manager.get_scannable_resource_classes()

class StorageResourceClassFields(AnonymousRequestHandler):
    @extract_request_args('plugin', 'resource_class')
    def run(self, request, plugin, resource_class):
        from configure.lib.storage_plugin.manager import storage_plugin_manager
        resource_klass, resource_klass_id = storage_plugin_manager.get_plugin_resource_class(plugin, resource_class)
        result = []
        for name, attr in resource_klass.get_sorted_attribute_items():
            if attr.label:
                label = attr.label
            else:
                words = name.split("_")
                label = " ".join([words[0].title()] + words[1:])

            result.append({
                'label': label,
                'name': name,
                'optional': attr.optional,
                'class': attr.__class__.__name__})
        return result

