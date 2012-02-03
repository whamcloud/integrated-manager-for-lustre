#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.contrib.contenttypes.models import ContentType

from configure.models import Command
from requesthandler import AnonymousRESTRequestHandler
from hydraapi.requesthandler import APIResponse


class Notifications(AnonymousRESTRequestHandler):
    def post(self, request, filter_opts):
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


class TransitionConsequences(AnonymousRESTRequestHandler):
    def post(self, request, id, content_type_id, new_state):
        from configure.lib.state_manager import StateManager
        ct = ContentType.objects.get_for_id(content_type_id)
        klass = ct.model_class()
        instance = klass.objects.get(pk = id)
        return StateManager().get_transition_consequences(instance, new_state)


class Transition(AnonymousRESTRequestHandler):
    def post(self, request, id, content_type_id, new_state):
        klass = ContentType.objects.get_for_id(content_type_id).model_class()
        instance = klass.objects.get(pk = id)

        command = Command.set_state(instance, new_state)
        return APIResponse(command.to_dict(), 202)


class ObjectSummary(AnonymousRESTRequestHandler):
    def post(self, request, objects):
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
