#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.contrib.contenttypes.models import ContentType

# Hydra server imports
import settings

from configure.models import Command
from requesthandler import AnonymousRequestHandler
from hydraapi.requesthandler import APIResponse


class SetTargetConfParams(AnonymousRequestHandler):
    def run(self, request, target_id, conf_params, IsFS):
        set_target_conf_param(target_id, conf_params, IsFS)


def set_target_conf_param(target_id, conf_params, IsFS):
    from configure.models import ManagedTarget, ManagedFilesystem, ManagedMdt, ManagedOst
    from django.shortcuts import get_object_or_404
    from configure.models import ApplyConfParams
    from configure.lib.conf_param import all_params
    from configure.lib.state_manager import StateManager

    if IsFS:
        target = get_object_or_404(ManagedFilesystem, pk = target_id)
    else:
        target = get_object_or_404(ManagedTarget, pk = target_id).downcast()

    def handle_conf_param(target, conf_params, mgs, **kwargs):
        for key, val in conf_params.items():
            model_klass, param_value_obj, help_text = all_params[key]
            p = model_klass(key = key,
                            value = val,
                            **kwargs)
            mgs.set_conf_params([p])
            StateManager().add_job(ApplyConfParams(mgs = mgs))

    if IsFS:
        handle_conf_param(target, conf_params, target.mgs.downcast(), filesystem = target)
    elif isinstance(target, ManagedMdt):
        handle_conf_param(target, conf_params, target.filesystem.mgs.downcast(), mdt = target)
    elif isinstance(target, ManagedOst):
        handle_conf_param(target, conf_params, target.filesystem.mgs.downcast(), ost = target)


class GetTargetConfParams(AnonymousRequestHandler):
    def run(self, request, target_id, kinds):
        from configure.lib.conf_param import (FilesystemClientConfParam,
                                              FilesystemGlobalConfParam,
                                              OstConfParam,
                                              MdtConfParam,
                                              get_conf_params,
                                              all_params)
        from configure.models import ManagedFilesystem, ManagedTarget, ManagedMdt, ManagedOst
        from django.shortcuts import get_object_or_404
        kind_map = {"FSC": FilesystemClientConfParam,
                    "FS": FilesystemGlobalConfParam,
                    "OST": OstConfParam,
                    "MDT": MdtConfParam}
        result = []

        def get_conf_param_for_target(target):
            conf_param_result = []
            for conf_param in target.get_conf_params():
                conf_param_result.append({'conf_param': conf_param.key,
                                          'value': conf_param.value,
                                          'conf_param_help': all_params[conf_param.key][2]
                                         }
                                        )
            return conf_param_result

        def search_conf_param(result, conf_param):
            for param in result:
                if param.get('conf_param') == conf_param:
                    return True
            return False

        # Create FS and Edit FS calls are passing kinds as ["FSC", "FS"]
        if kinds == ["FS", "FSC"] and target_id:
                target = get_object_or_404(ManagedFilesystem, pk = target_id).downcast()
                result.extend(get_conf_param_for_target(target))
        elif target_id:
            target = get_object_or_404(ManagedTarget, pk = target_id).downcast()
            if isinstance(target, ManagedMdt):
                result.extend(get_conf_param_for_target(target))
                kinds = ["MDT"]
            elif isinstance(target, ManagedOst):
                result.extend(get_conf_param_for_target(target))
                kinds = ["OST"]
            else:
                return result

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
                if not search_conf_param(result, conf_param):
                    result.append({'conf_param': conf_param, 'value': '', 'conf_param_help': all_params[conf_param][2]})
        return result


class GetTargetResourceGraph(AnonymousRequestHandler):
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

            this_row.sort(lambda a, b: cmp(nextrow_affinity(a), nextrow_affinity(b)))

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
                    'icon': "%simages/storage_plugin/%s.png" % (settings.STATIC_URL, resource.icon),
                    'type': resource.get_class_label(),
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


class Notifications(AnonymousRequestHandler):
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
    def run(self, request, id, content_type_id, new_state):
        from configure.lib.state_manager import StateManager
        ct = ContentType.objects.get_for_id(content_type_id)
        klass = ct.model_class()
        instance = klass.objects.get(pk = id)
        return StateManager().get_transition_consequences(instance, new_state)


class Transition(AnonymousRequestHandler):
    def run(self, request, id, content_type_id, new_state):
        klass = ContentType.objects.get_for_id(content_type_id).model_class()
        instance = klass.objects.get(pk = id)

        command = Command.set_state(instance, new_state)
        return APIResponse(command.to_dict(), 202)


class ObjectSummary(AnonymousRequestHandler):
    def run(self, request, objects):
        result = []
        for o in objects:
            from configure.lib.state_manager import StateManager
            klass = ContentType.objects.get_for_id(o['content_type_id']).model_class()
            try:
                instance = klass.objects.get(pk = o['id'])
            except klass.DoesNotExist:
                continue

            result.append({'id': o['id'],
                           'content_type_id': o['content_type_id'],
                           'label': instance.get_label(),
                           'state': instance.state,
                           'available_transitions': StateManager.available_transitions(instance)})
        return result
