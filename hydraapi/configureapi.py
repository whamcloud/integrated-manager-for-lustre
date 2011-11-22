#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
#REST API Controller for Lustre File systems resource in configure namespace
from django.core.management import setup_environ
from django.contrib.contenttypes.models import ContentType

# Hydra server imports
import settings
setup_environ(settings)

from configure.models import ManagedHost
from configure.lib.state_manager import (StateManager)
from requesthandler import (AnonymousRequestHandler,
                            extract_request_args)

class TestHost(AnonymousRequestHandler):
    @extract_request_args('hostname')
    def run(self,request,hostname):
        from monitor.tasks import test_host_contact
        from configure.models import Monitor
        host = ManagedHost(address = hostname)
        host.monitor = Monitor(host = host)
        job = test_host_contact.delay(host)
        return {'task_id': job.task_id, 'status': job.status}

class AddHost(AnonymousRequestHandler):
    @extract_request_args('hostname')
    def run(self,request,hostname):
        host = ManagedHost.create_from_string(hostname)
        return {'host_id':host.id, 'host': host.address, 'status': 'added'}

class RemoveHost(AnonymousRequestHandler):
    @extract_request_args('hostid')
    def run(self,request,hostid):
        host =  ManagedHost.objects.get(id = hostid)
        transition_job = StateManager.set_state(host,'removed')
        return {'hostid': hostid,'job_id': transition_job.task_id,'status': transition_job.status}

class SetLNetStatus(AnonymousRequestHandler):
    @extract_request_args('hostid','state')
    def run(self,request,hostid,state):
        host =  ManagedHost.objects.get(id = hostid)
        transition_job = StateManager.set_state(host,state)
        return {'hostid': hostid,'job_id': transition_job.task_id,'status': transition_job.status}

class SetTargetMountStage(AnonymousRequestHandler):
    @extract_request_args('target_id','state')
    def run(self,request,target_id,state):
        from configure.models import ManagedTarget
        target = ManagedTarget.objects.get(id=target_id)                       
        transition_job = StateManager.set_state(target.downcast(),state)
        return {'target_id': target_id,'job_id': transition_job.task_id,'status': transition_job.status}
                   
class RemoveFileSystem(AnonymousRequestHandler):
    @extract_request_args('filesystemid')
    def run(self,request,filesystemid):
        from configure.models import ManagedFilesystem
        from configure.models.state_manager import StateManager
        fs = ManagedFilesystem.objects.get(id = filesystemid)    
        transition_job = StateManager.set_state(fs,'removed')
        return {'filesystemid': filesystemid,'job_id': transition_job.task_id,'status': transition_job.status}

class RemoveClient(AnonymousRequestHandler):
    @extract_request_args('clientid')
    def run(self,request,clientid):
        from configure.models import ManagedTargetMount
        from configure.models.state_manager import StateManager
        mtm = ManagedTargetMount.objects.get(id = clientid)
        transition_job = StateManager.set_state(mtm,'removed')
        return {'clientid': clientid,'job_id': transition_job.task_id,'status': transition_job.status}

class GetJobStatus(AnonymousRequestHandler):
    @extract_request_args('job_id')
    def run(self,request,job_id):
        from django.shortcuts import get_object_or_404
        from configure.models import Job
        job = get_object_or_404(Job, id = job_id)
        job = job.downcast()
        return {'job_status': job.status,'job_info': job.info,'job_result': job.result}

class SetJobStatus(AnonymousRequestHandler):
    @extract_request_args('job_id','state')
    def run(self,request,job_id,state):
        assert state in ['pause','cancel','resume']
        from django.shortcuts import get_object_or_404
        from configure.models import Job
        job = get_object_or_404(Job, id = job_id)
        if state == 'pause':
            job.pause()
        elif state == 'cancel':
            job.cancel()   
        else: 
            job.resume() 
        return {'transition_job_status': job.status,'job_info': job.info,'job_result': job.result}

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

        rows = []
        from django.utils.html import conditional_escape
        from configure.lib.storage_plugin.query import ResourceQuery
        for record in ResourceQuery().get_class_resources(resource_class_id):
            resource = record.to_resource()
            alias = conditional_escape(record.alias_or_name(resource))
            alias_markup = "<a class='storage_resource' href='#%s'>%s</a>" % (record.pk, alias)

            # NB What we output here is logically markup, not strings, so we escape.
            # (underlying storage_plugin.attributes do their own escaping
            row = {
                    'id': record.pk,
                    'content_type_id': ContentType.objects.get_for_model(record).id,
                    '_alias': alias_markup,
                    0: 'wtf'
                    }
            for c in attr_columns:
                row[c['name']] = resource.format(c['name'])

            row['_alerts'] = [a.to_dict() for a in ResourceQuery().resource_get_alerts(resource)]
                
            rows.append(row)    

        columns = [{'mdataProp': 'id', 'bVisible': False}, {'mDataProp': '_alias', 'sTitle': 'Name'}]
        for c in attr_columns:
            columns.append({'sTitle': c['label'], 'mDataProp': c['name']})
        return {'aaData': rows, 'aoColumns': columns}

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

        return {'id': record.pk,
                'content_type_id': ContentType.objects.get_for_model(record).id,
                'class_name': resource.human_class(),
                'alias': record.alias,
                'default_alias': record.to_resource().human_string(),
                'attributes': resource.get_attribute_items(),
                'alerts': alerts,
                'stats': stats,
                'charts': resource.get_charts(),
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

class CreateNewFilesystem(AnonymousRequestHandler):
    @extract_request_args('fsname','mgt_id','mgt_lun_id','mdt_lun_id','ost_lun_ids')
    def run(self, request, fsname, mgt_id, mgt_lun_id, mdt_lun_id, ost_lun_ids):
        # mgt_id and mgt_lun_id are mutually exclusive:
        # * mgt_id is a PK of an existing ManagedMgt to use
        # * mgt_lun_id is a PK of a Lun to use for a new ManagedMgt
        assert bool(mgt_id) != bool(mgt_lun_id)

        from configure.models import ManagedMgs, ManagedMdt, ManagedOst

        if not mgt_id:
            mgt = create_target(mgt_lun_id, ManagedMgs, name="MGS")
            mgt_id = mgt.pk
        else:
            mgt_lun_id = ManagedMgs.objects.get(pk = mgt_id).get_lun()

        # This is a brute safety measure, to be superceded by 
        # some appropriate validation that gives a helpful
        # error to the user.
        all_lun_ids = [mgt_lun_id] + [mdt_lun_id] + ost_lun_ids
        # Test that all values in all_lun_ids are unique
        assert len(set(all_lun_ids)) == len(all_lun_ids)
        
        from django.db import transaction
        with transaction.commit_on_success():
            fs = create_fs(mgt_id, fsname)
            mdt = create_target(mdt_lun_id, ManagedMdt, filesystem = fs)
            osts = []
            for lun_id in ost_lun_ids:
                osts.append(create_target(lun_id, ManagedOst, filesystem = fs))
        # Important that a commit happens here so that the targets
        # land in DB before the set_state jobs act upon them.

        from configure.lib.state_manager import StateManager
        StateManager.set_state(mdt, 'mounted')
        for target in osts:
            StateManager.set_state(target, 'mounted')

        return fs.pk

class CreateFilesystem(AnonymousRequestHandler):
    @extract_request_args('mgs_id','fsname')
    def run(self,request,mgs_id,fsname):
        create_fs(mgs_id,fsname)

def create_fs(mgs_id,fsname):
        from configure.models import ManagedFilesystem, ManagedMgs
        mgs = ManagedMgs.objects.get(id=mgs_id)
        fs = ManagedFilesystem(mgs=mgs,name = fsname)
        fs.save()
        return fs

class CreateMGT(AnonymousRequestHandler):
    @extract_request_args('lun_id')
    def run(self, request, lun_id):
        from configure.models import ManagedMgs
        mgt = create_target(lun_id, ManagedMgs, name = "MGS")

        from django.db import transaction
        transaction.commit()

        from configure.lib.state_manager import StateManager
        StateManager.set_state(mgt, 'mounted')


def create_target(lun_id, target_klass, **kwargs):
    from configure.models import Lun, ManagedTargetMount

    target = target_klass(**kwargs)
    target.save()

    lun = Lun.objects.get(pk = lun_id)
    for node in lun.lunnode_set.all():
        if node.use:
            mount = ManagedTargetMount(
                block_device = node,
                target = target,
                host = node.host,
                mount_point = target.default_mount_path(node.host),
                primary = node.primary)
            mount.save()

    return target

class CreateOSTs(AnonymousRequestHandler):
    @extract_request_args('filesystem_id', 'ost_lun_ids')
    def run(self, request, filesystem_id, ost_lun_ids):
        from configure.models import ManagedFilesystem, ManagedOst
        fs = ManagedFilesystem.objects.get(id=filesystem_id)
        osts = []
        for lun_id in ost_lun_ids:
            osts.append(create_target(lun_id, ManagedOst, filesystem = fs))

        from django.db import transaction
        transaction.commit()

        from configure.lib.state_manager import StateManager
        for target in osts:
            StateManager.set_state(target, 'mounted')

class SetTargetConfParams(AnonymousRequestHandler):
    @extract_request_args('target_id', 'conf_params')
    def run(self, request, target_id, conf_params):
        from configure.models import ManagedTarget,ManagedFilesystem,ManagedMdt,ManagedOst
        from django.shortcuts import get_object_or_404
        from configure.models import ApplyConfParams
        from configure.lib.conf_param import all_params
        from configure.lib.state_manager import StateManager
        
        target = get_object_or_404(ManagedTarget, pk = target_id).downcast()
        
        def handle_conf_param(target,conf_params,mgs,**kwargs):
            for k,v in conf_params:
                 model_klass, param_value_obj, help_text = all_params[k]
                 p = model_klass(key = k,
                                 value = v,
                                 **kwargs)
                 mgs.set_conf_params([p])
                 StateManager().add_job(ApplyConfParams(mgs = mgs))
        
        if isinstance(target, ManagedMdt):
            handle_conf_param(target,conf_params,target.filesystem.mgs.downcast(),mdt = target)
        elif (type(target.downcast().__class__) == ManagedOst):
            handle_conf_param(target,conf_params,target.filesystem.mgs.downcast(),ost = target)
        else:
            fs = ManagedFilesystem.objects.get(id=target_id)
            handle_conf_param(target,conf_params,fs.mgs.downcast(),filesystem = fs)

class GetTargetConfParams(AnonymousRequestHandler):
    @extract_request_args('target_id', 'kinds')
    def run(self, request, target_id, kinds):
        from configure.lib.conf_param import (FilesystemClientConfParam,
                                              FilesystemGlobalConfParam,
                                              OstConfParam,
                                              MdtConfParam,
                                              get_conf_params,
                                              all_params)
        from configure.models import ManagedTarget,ManagedMdt,ManagedOst 
        from django.shortcuts import get_object_or_404        
        kind_map = {"FSC":FilesystemClientConfParam,
                    "FS": FilesystemGlobalConfParam,
                    "OST":OstConfParam,
                    "MDT":MdtConfParam}
        result = []
        
        def get_conf_param_for_target(target):
            conf_param_result = []
            for conf_param in target.get_conf_params():
                conf_param_result.append({'conf_param':conf_param.key,
                                          'value':conf_param.value,
                                          'conf_param_help':all_params[conf_param.key][2]
                                         }
                                        )
            return conf_param_result  
        
        if target_id:
            target = get_object_or_404(ManagedTarget, pk = target_id).downcast() 
            if isinstance(target, ManagedMdt):
                result.extend(get_conf_param_for_target(target))
                kinds = ["MDT"]
            elif isinstance(target, ManagedOst):
                result.extend(get_conf_param_for_target(target))
                kinds = ["OST"]
            else:
                return result
        #Fix me: Need a way to identify if the target is Filesystem or MGS    
        if kinds:
            klasses = []
            for kind in kinds:
                try:
                    klasses.append(kind_map[kind])
                except KeyError:
                    raise RuntimeError("Unknown target kind '%s' (kinds are %s)" % (kind, kind_map.keys()))
        else:
            klasses = kind_map.values()
        for klass in klasses:
            conf_params = get_conf_params([klass])
            for conf_param in conf_params:
                if not result.__contains__(conf_params): 
                    result.append({'conf_param':conf_param,'value':'','conf_param_help':all_params[conf_param][2]}) 
        return result

class Target(AnonymousRequestHandler):
    @extract_request_args('id')
    def run(self, request, id):
        from configure.models import ManagedTarget
        from django.shortcuts import get_object_or_404
        target = get_object_or_404(ManagedTarget, pk = id).downcast()
        return target.to_dict()

class GetTargetResourceGraph(AnonymousRequestHandler):
    @extract_request_args('target_id')
    def run(self, request, target_id):
        from monitor.models import AlertState
        from configure.models import ManagedTarget
        from django.shortcuts import get_object_or_404
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
        for name, attr in resource_klass.get_all_attribute_properties():
            result.append({
                'label': attr.get_label(name),
                'name': name,
                'optional': attr.optional,
                'class': attr.__class__.__name__})
        return result

class Notifications(AnonymousRequestHandler):
    @extract_request_args('filter_opts')
    def run(self, request, filter_opts):
        since_time = filter_opts['since_time']
        initial = filter_opts['initial']
        # last_check should be a string in the datetime.isoformat() format
        # TODO: use dateutils.parser to accept general ISO8601 (see
        # note in hydracm.context_processors.page_load_time)
        assert (since_time or initial)

        alert_filter_args = []
        alert_filter_kwargs = {}
        job_filter_args = []
        job_filter_kwargs = {}
        if since_time:
            from datetime import datetime
            since_time = datetime.strptime(since_time, "%Y-%m-%dT%H:%M:%S")
            job_filter_kwargs['modified_at__gte'] = since_time
            alert_filter_kwargs['end__gte'] = since_time

        if initial:
            from django.db.models import Q
            job_filter_args.append(~Q(state = 'complete'))
            alert_filter_kwargs['active'] = True

        from configure.models import Job
        jobs = Job.objects.filter(*job_filter_args, **job_filter_kwargs).order_by('-modified_at')
        from monitor.models import AlertState
        alerts = AlertState.objects.filter(*alert_filter_args, **alert_filter_kwargs).order_by('-end')

        # >> FIXME HYD-421 Hack: this info should be provided in a more generic way by 
        #    AlertState subclasses
        # NB adding a 'what_do_i_affect' method to 
        alert_dicts = []
        for a in alerts:
            a = a.downcast()
            alert_dict = a.to_dict()

            affected_objects = set()

            from configure.models import StorageResourceAlert, StorageAlertPropagated
            from configure.models import Lun
            from configure.models import ManagedTargetMount, ManagedMgs
            from configure.models import FilesystemMember
            from monitor.models import TargetOfflineAlert, TargetRecoveryAlert, TargetFailoverAlert, HostContactAlert

            def affect_target(target):
                target = target.downcast()
                affected_objects.add(target)
                if isinstance(target, FilesystemMember):
                    affected_objects.add(target.filesystem)
                elif isinstance(target, ManagedMgs):
                    for fs in target.managedfilesystem_set.all():
                        affected_objects.add(fs)

            if isinstance(a, StorageResourceAlert):
                affected_srrs = [sap['storage_resource_id'] for sap in StorageAlertPropagated.objects.filter(alert_state = a).values('storage_resource_id')]
                affected_srrs.append(a.alert_item_id)
                luns = Lun.objects.filter(storage_resource__in = affected_srrs)
                for l in luns:
                    for ln in l.lunnode_set.all():
                        tms = ManagedTargetMount.objects.filter(block_device = ln)
                        for tm in tms:
                            affect_target(tm.target)
            elif isinstance(a, TargetFailoverAlert):
                affect_target(a.alert_item.target)
            elif isinstance(a, TargetOfflineAlert) or isinstance(a, TargetRecoveryAlert):
                affect_target(a.alert_item)
            elif isinstance(a, HostContactAlert):
                tms = ManagedTargetMount.objects.filter(host = a.alert_item)
                for tm in tms:
                    affect_target(tm.target)

            alert_dict['affected'] = []
            alert_dict['affected'].append([a.alert_item_id, a.alert_item_type_id])
            for ao in affected_objects:
                from django.contrib.contenttypes.models import ContentType
                ct = ContentType.objects.get_for_model(ao)
                alert_dict['affected'].append([ao.pk, ct.pk])

            alert_dicts.append(alert_dict)
        # << 

        if jobs.count() > 0 and alerts.count() > 0:
            latest_job = jobs[0]
            latest_alert = alerts[0]
            last_modified = max(latest_job.modified_at, latest_alert.end)
        elif jobs.count() > 0:
            latest_job = jobs[0]
            last_modified = latest_job.modified_at
        elif alerts.count() > 0:
            latest_alert = alerts[0]
            last_modified = latest_alert.end
        else:
            last_modified = None

        if last_modified:
            from monitor.lib.util import time_str
            last_modified = time_str(last_modified)

        return {
                'last_modified': last_modified,
                'jobs': [job.to_dict() for job in jobs],
                'alerts': alert_dicts
                }

class TransitionConsequences(AnonymousRequestHandler):        
    @extract_request_args('id', 'content_type_id', 'new_state')
    def run(self, request, id, content_type_id, new_state):
        from configure.lib.state_manager import StateManager
        ct = ContentType.objects.get_for_id(content_type_id)
        klass = ct.model_class()
        instance = klass.objects.get(pk = id)
        return StateManager().get_transition_consequences(instance, new_state)

class Transition(AnonymousRequestHandler):
    @extract_request_args('id','content_type_id', 'new_state')
    def run(self, request, id, content_type_id, new_state):
        from configure.lib.state_manager import StateManager
        klass = ContentType.objects.get_for_id(content_type_id).model_class()
        instance = klass.objects.get(pk = id)
        StateManager.set_state(instance, new_state)

        return None

class ObjectSummary(AnonymousRequestHandler):
    @extract_request_args('objects')
    def run(self, request, objects):
        result = []
        for o in objects:
            from configure.lib.state_manager import StateManager
            klass = ContentType.objects.get_for_id(o['content_type_id']).model_class()
            instance = klass.objects.get(pk = o['id'])

            result.append({'id': o['id'],
                           'content_type_id': o['content_type_id'],
                           'human_name': instance.human_name(),
                           'state': instance.state,
                           'available_transitions': StateManager.available_transitions(instance)})
        return result 

