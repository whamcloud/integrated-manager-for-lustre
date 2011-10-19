
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseBadRequest
from django.db import transaction
from django import forms

from monitor.models import *
from configure.models import *

# IMPORTANT
# These views are implicitly transactions.  If you create an object and then 
# submit a celery job that does something to it, the job could execute before
# the transaction is committed, and fail because the object doesn't exist.
# If you create an object which you're going to refer to in a celery job,
# then commit your transaction before starting your celery job

def _create_target_mounts(node, target, failover_host = None):
    primary = ManagedTargetMount(
        block_device = node,
        target = target,
        host = node.host, 
        mount_point = target.default_mount_path(node.host),
        primary = True)
    primary.save()

    if failover_host:
        failover_node = LunNode.objects.get(lun = node.lun, host = failover_host)
        failover = ManagedTargetMount(
            block_device = failover_node,
            target = target,
            host = failover_host, 
            mount_point = target.default_mount_path(failover_host),
            primary = False)
        failover.save()
        return [primary, failover]
    else:
        return [primary]

def _set_target_states(form, targets, mounts):
    assert(isinstance(form, CreateTargetsForm))
    from configure.lib.state_manager import StateManager
    if form.cleaned_data['start_now']:
        for target in targets:
            StateManager.set_state(target, 'mounted')
    elif form.cleaned_data['register_now']:
        for target in targets:
            StateManager.set_state(target, 'unmounted')
    elif form.cleaned_data['format_now']:
        for target in targets:
            StateManager.set_state(target, 'formatted')


class CreateTargetsForm(forms.Form):
    format_now = forms.BooleanField(required = False, initial = True)
    register_now = forms.BooleanField(required = False, initial = True)
    start_now = forms.BooleanField(required = False, initial = True)

    def clean(self):
        cleaned_data = self.cleaned_data
        format_now = cleaned_data.get("format_now")
        register_now = cleaned_data.get("register_now")
        start_now = cleaned_data.get("start_now")

        if register_now and not format_now:
            raise forms.ValidationError("A target must be formatted to be registered.")

        return cleaned_data

def create_mgs(request, host_id):
    host = get_object_or_404(Host, id = int(host_id))
    nodes = host.available_lun_nodes()
    other_hosts = [h for h in Host.objects.all() if h.id != host.id]

    class CreateMgsForm(CreateTargetsForm):
        device = forms.ChoiceField(choices = [(n.id, n.pretty_string()) for n in nodes])
        failover_partner = forms.ChoiceField(choices = [(None, 'None')] + [(h.id, h) for h in other_hosts])

    if request.method == 'GET':
        form = CreateMgsForm()
    elif request.method == 'POST':
        form = CreateMgsForm(request.POST)
        if form.is_valid():
            node = LunNode.objects.get(id = form.cleaned_data['device'])
            if form.cleaned_data['failover_partner'] and form.cleaned_data['failover_partner'] != 'None':
                failover_host = Host.objects.get(id = form.cleaned_data['failover_partner'])
            else:
                failover_host = None

            target = ManagedMgs(name='MGS')
            target.save()
            mounts = _create_target_mounts(node, target, failover_host)

            # Commit before spawning celery tasks
            transaction.commit()
            _set_target_states(form, [target], mounts)

            return redirect('configure.views.states')

    else:
        return HttpResponseBadRequest

    return render_to_response("create_mgs.html", RequestContext(request, {
        'host': host,
        'nodes': nodes,
        'other_hosts': other_hosts,
        'form': form
        }))

def create_fs(request, mgs_id):
    mgs = get_object_or_404(ManagementTarget, id = int(mgs_id))

    class CreateFsForm(forms.Form):
        name = forms.CharField(min_length = 1, max_length = 8)

    if request.method == 'GET':
        form = CreateFsForm()
    elif request.method == 'POST':
        form = CreateFsForm(request.POST)
        if form.is_valid():
            fs = ManagedFilesystem(mgs = mgs, name = form.cleaned_data['name'])
            fs.save()
            return redirect('configure.views.states')
    else:
        return HttpResponseBadRequest

    return render_to_response("create_fs.html", RequestContext(request, {
        'mgs': mgs,
        'form': form
        }))

def create_oss(request, host_id):
    host = get_object_or_404(Host, id = int(host_id))
    nodes = host.available_lun_nodes()
    other_hosts = [h for h in Host.objects.all() if h.id != host.id]

    class CreateOssForm(CreateTargetsForm):
        filesystem = forms.ChoiceField(choices = [(f.id, f.name) for f in ManagedFilesystem.objects.all()])
        failover_partner = forms.ChoiceField(choices = [(None, 'None')] + [(h.id, h) for h in other_hosts])
        def __init__(self, *args, **kwargs):
            super(CreateTargetsForm, self).__init__(*args, **kwargs)
            self.fields.keyOrder = ['filesystem', 'failover_partner', 'format_now', 'register_now', 'start_now']
        
    class CreateOssNodeForm(forms.Form):
        def __init__(self, node, *args, **kwargs):
            self.node = node
            super(CreateOssNodeForm, self).__init__(*args, **kwargs)
        use = forms.BooleanField(required=False)

    if request.method == 'GET':
        node_forms = []
        for node in nodes:
            node_forms.append(CreateOssNodeForm(node, initial = {
                'node_id': node.id,
                'node_name': node.pretty_string(),
                'use': False
                }, prefix = "%d" % node.id))

        form = CreateOssForm(prefix = 'create')
    elif request.method == 'POST':
        node_forms = []
        for node in nodes:
            node_form = CreateOssNodeForm(node, data = request.POST, prefix = "%d" % node.id)
            # These are just checkboxes
            assert(node_form.is_valid())
            node_forms.append(node_form)
        form = CreateOssForm(request.POST, prefix = 'create')
        if form.is_valid():
            if form.cleaned_data['failover_partner'] and form.cleaned_data['failover_partner'] != 'None':
                failover_host = Host.objects.get(id = form.cleaned_data['failover_partner'])
            else:
                failover_host = None
            filesystem = ManagedFilesystem.objects.get(id=form.cleaned_data['filesystem'])

            all_targets = []
            all_mounts = []
            for node_form in node_forms:
                if node_form.cleaned_data['use']:
                    node = node_form.node
                    target = ManagedOst(filesystem = filesystem)
                    target.save()
                    all_targets.append(target)
                    mounts = _create_target_mounts(node, target, failover_host)
                    all_mounts.extend(mounts)

            # Commit before spawning celery tasks
            transaction.commit()
            _set_target_states(form, all_targets, all_mounts)
            return redirect('configure.views.states')
    else:
        return HttpResponseBadRequest

    return render_to_response("create_oss.html", RequestContext(request, {
        'host': host,
        'form': form,
        'node_forms': node_forms
        }))

def create_mds(request, host_id):
    host = get_object_or_404(Host, id = int(host_id))
    nodes = host.available_lun_nodes()
    other_hosts = [h for h in Host.objects.all() if h.id != host.id]

    filesystems = []
    for f in ManagedFilesystem.objects.all():
        try:
            ManagedMdt.objects.get(filesystem = f)
        except ManagedMdt.DoesNotExist:
            filesystems.append(f)

    class CreateMdtForm(CreateTargetsForm):
        filesystem = forms.ChoiceField(choices = [(f.id, f.name) for f in filesystems])
        device = forms.ChoiceField(choices = [(n.id, n.pretty_string()) for n in nodes])
        failover_partner = forms.ChoiceField(choices = [(None, 'None')] + [(h.id, h) for h in other_hosts])

    if request.method == 'GET':
        form = CreateMdtForm()
    elif request.method == 'POST':
        form = CreateMdtForm(request.POST)

        if form.is_valid():
            node = LunNode.objects.get(id = form.cleaned_data['device'])
            if form.cleaned_data['failover_partner'] and form.cleaned_data['failover_partner'] != 'None':
                failover_host = Host.objects.get(id = form.cleaned_data['failover_partner'])
            else:
                failover_host = None
            filesystem = ManagedFilesystem.objects.get(id=form.cleaned_data['filesystem'])

            target = ManagedMdt(filesystem = filesystem)
            target.save()
            mounts = _create_target_mounts(node, target, failover_host)

            # Commit before spawning celery tasks
            transaction.commit()
            _set_target_states(form, [target], mounts)

            return redirect('configure.views.states')
    else:
        return HttpResponseBadRequest

    return render_to_response("create_mds.html", RequestContext(request, {
        'host': host,
        'form': form
        }))

def jobs(request):
    jobs = Job.objects.all().order_by("-id")
    return render_to_response("jobs.html", RequestContext(request, {
        'jobs': jobs
        }))

def _jobs_json():
    import json
    from django.core.urlresolvers import reverse
    from datetime import timedelta, datetime
    from django.db.models import Q
    jobs = Job.objects.filter(~Q(state = 'complete') | Q(created_at__gte=datetime.now() - timedelta(minutes=60)))
    jobs_dicts = []
    for job in jobs:
        actions = []
        if job.state != 'complete':
            actions.append({
                'url': reverse('configure.views.job_cancel', kwargs={"job_id": job.id}),
                'caption': "Cancel"})
        if job.state == 'pending':
            actions.append({
                'url': reverse('configure.views.job_pause', kwargs={"job_id": job.id}),
                'caption': "Pause"})
        if job.state == 'paused':
            actions.append({
                'url': reverse('configure.views.job_unpause', kwargs={"job_id": job.id}),
                'caption': "Unpause"})

        jobs_dicts.append({
            'id': job.id,
            'state': job.state,
            'errored': job.errored,
            'cancelled': job.cancelled,
            'created_at': "%s" % job.created_at,
            'description': job.description(),
            'actions': actions
        })
    jobs_json = json.dumps(jobs_dicts)

    from configure.lib.state_manager import StateManager
    state_manager = StateManager()

    from itertools import chain
    stateful_objects = []
    klasses = [ManagedOst, ManagedMdt, ManagedMgs, ManagedHost, ManagedTargetMount, ManagedFilesystem]
    can_create_mds = (MetadataTarget.objects.count() != ManagedFilesystem.objects.count())
    can_create_oss = MetadataTarget.objects.count() > 0
    for i in chain(*[k.objects.all() for k in klasses]):
        actions = []
        if isinstance(i, StatefulObject):
            state = i.state
            transitions = state_manager.available_transitions(i)
            if transitions == None:
                busy = True
            else:
                busy = False
                for transition in transitions:
                    actions.append({
                        "name": transition['state'],
                        "caption": transition['verb'],
                        "url": reverse('configure.views.set_state', kwargs={
                            "content_type_id": "%s" % i.content_type_id,
                            "stateful_object_id": "%s" % i.id,
                            "new_state": transition['state']
                            }),
                        "ajax": True
                        })
        else:
            state = ""
        
        if isinstance(i, ManagedMgs):
            actions.append({
                "name": "create_fs",
                "caption": "Create filesystem",
                "url": reverse('configure.views.create_fs', kwargs={"mgs_id": i.id}),
                "ajax": False
                })
        if isinstance(i, ManagedHost):
            if not i.is_mgs():
                actions.append({
                    "name": "create_mgs",
                    "caption": "Setup MGS",
                    "url": reverse('configure.views.create_mgs', kwargs={"host_id": i.id}),
                    "ajax": False
                    })
            if can_create_mds:
                actions.append({
                    "name": "create_mgs",
                    "caption": "Setup MDS",
                    "url": reverse('configure.views.create_mds', kwargs={"host_id": i.id})
                    })

            if can_create_oss:
                actions.append({
                    "name": "create_mgs",
                    "caption": "Setup OSS",
                    "url": reverse('configure.views.create_oss', kwargs={"host_id": i.id})
                    })
                
        if isinstance(i, ManagedFilesystem): 
            url = reverse('configure.views.filesystem', kwargs={"filesystem_id": i.id})
        elif isinstance(i, ManagedTarget):
            url = reverse('configure.views.target', kwargs={"target_id": i.id})
        else:
            url = None

        stateful_objects.append({
            "id": i.id,
            "__str__": "%s" % i,
            "state": state,
            "actions": actions,
            "content_type_id": ContentType.objects.get_for_model(i).id,
            "busy": busy,
            "url": url
            })

    return json.dumps({
                'jobs': jobs_dicts,
                'stateful_objects': stateful_objects
            }, indent = 4)

def jobs_json(request):
    return HttpResponse(_jobs_json(), 'application/json')


def job(request, job_id):
    job = get_object_or_404(Job, id = job_id)
    job = job.downcast()

    return render_to_response("job.html", RequestContext(request, {
        'job': job
        }))

class ConfParamForm(forms.Form):
    value = forms.CharField(min_length = 0, max_length = 512)

    def clean(self):
        from configure.lib.conf_param import all_params
        cleaned_data = self.cleaned_data
        key = cleaned_data.get('key')
        try:
            model_klass, param_value_obj, help_text = all_params[key]
        except KeyError:
            self._errors["key"] = self.error_class(["Key '%s' unknown" % key])
            del cleaned_data['key']
            return cleaned_data

        value = cleaned_data.get('value')
        try:
            param_value_obj.validate(value)
        except ValueError, param_error:
            self._errors["value"] = self.error_class([param_error.__str__()])
            del cleaned_data['value']

        return cleaned_data

    def save(self, mgs, **kwargs):
        key = self.cleaned_data['key']
        value = self.cleaned_data['value']

        from configure.lib.conf_param import all_params
        model_klass, param_value_obj, help_text = all_params[key]

        # TODO: avoid using "" to signify param removal, so that 
        # params can in theory be set to empty strings
        if len(value) == 0:
            value = None

        p = model_klass(
                key = key,
                value = value,
                **kwargs)
        mgs.downcast().set_conf_params([p])

def _handle_conf_param_form(request, mgs, form_klass, **kwargs):
    if request.method == 'GET':
        form = form_klass()
    elif request.method == 'POST':
        form = form_klass(data = request.POST)
        if form.is_valid():
            form.save(mgs, **kwargs)
            from configure.models import ApplyConfParams
            from configure.lib.state_manager import StateManager
            StateManager().add_job(ApplyConfParams(mgs = mgs))
            form = form_klass()

    return form

def filesystem(request, filesystem_id):
    filesystem = get_object_or_404(ManagedFilesystem, id = filesystem_id)

    from configure.lib.conf_param import get_conf_params
    class FilesystemConfParamForm(ConfParamForm):
        key = forms.ChoiceField(choices = [(i,i) for i in get_conf_params([FilesystemClientConfParam, FilesystemGlobalConfParam])])

    conf_param_form = _handle_conf_param_form(request, filesystem.mgs.downcast(), FilesystemConfParamForm, filesystem = filesystem)
    
    return render_to_response("filesystem.html", RequestContext(request, {
        'filesystem': filesystem,
        'conf_param_list': filesystem.get_conf_params(),
        'conf_param_form': conf_param_form
        }))

def target(request, target_id):
    from monitor.models import Target
    target = get_object_or_404(Target, pk = target_id).downcast()
    assert(isinstance(target, ManagedTarget))

    from configure.lib.conf_param import get_conf_params
    if isinstance(target, ManagedMgs):
        conf_param_form = None
    elif isinstance(target, ManagedMdt):
        # Create a variant of ConfParamForm showing the options available
        # for an MDT
        class MdtConfParamForm(ConfParamForm):
            key = forms.ChoiceField(choices = [(i,i) for i in get_conf_params([MdtConfParam])])

        conf_param_form = _handle_conf_param_form(
                request,
                target.filesystem.mgs.downcast(),
                MdtConfParamForm,
                mdt = target)
    elif isinstance(target, ManagedOst):
        # Create a variant of ConfParamForm showing the options available
        # for an OST
        class OstConfParamForm(ConfParamForm):
            key = forms.ChoiceField(choices = [(i,i) for i in get_conf_params([OstConfParam])])

        conf_param_form = _handle_conf_param_form(
                request,
                target.filesystem.mgs.downcast(),
                OstConfParamForm,
                ost = target)
    else:
        raise NotImplementedError

    ancestor_records = set()
    parent_records = set()
    storage_alerts = set()
    lustre_alerts = set(AlertState.filter_by_item(target))
    from collections import defaultdict
    rows = defaultdict(list)
    id_edges = []
    for tm in target.targetmount_set.all():
        lustre_alerts |= set(AlertState.filter_by_item(tm))
        lun_node = tm.block_device
        if lun_node.storage_resource_id:
            from configure.lib.storage_plugin.query import ResourceQuery

            parent_record = StorageResourceRecord.objects.get(pk = lun_node.storage_resource_id)
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
    box_height = 40
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
            nodes.append({
                'left': x,
                'top': y,
                'title': record.alias_or_name(),
                'icon': "%simages/storage_plugin/%s.png" % (STATIC_URL, resource.icon),
                'type': resource.human_class(),
                'id': record.id
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

    return render_to_response("target.html", RequestContext(request, {
        'target': target,
        'conf_param_list': target.get_conf_params(),
        'conf_param_form': conf_param_form,
        'parent_records': parent_records,
        'ancestor_records': ancestor_records,
        'storage_alerts': storage_alerts,
        'lustre_alerts': lustre_alerts,
        'rows': dict(rows),
        'graph': graph,
        'target_size': target.targetmount_set.get(primary = True).block_device.lun.size}))


def states(request):
    return render_to_response("states.html", RequestContext(request, {
        'initial_data': _jobs_json()
        }))

def set_state(request, content_type_id, stateful_object_id, new_state):
    stateful_object_klass = ContentType.objects.get(id = content_type_id).model_class()
    stateful_object = stateful_object_klass.objects.get(id = stateful_object_id)

    from configure.lib.state_manager import StateManager
    transition_job = StateManager.set_state(stateful_object, new_state)

    return HttpResponse(status = 201)

def job_cancel(request, job_id):
    job = get_object_or_404(Job, pk = job_id)
    job.cancel()

    return HttpResponse(status = 200)

def job_pause(request, job_id):
    job = get_object_or_404(Job, pk = job_id)
    job.pause()

    return HttpResponse(status = 200)

def job_unpause(request, job_id):
    job = get_object_or_404(Job, pk = job_id)
    job.unpause()

    return HttpResponse(status = 200)

def conf_param_help(request, conf_param_name):
    try:
        from configure.lib.conf_param import all_params
        model_klass, param_value_obj, help_text = all_params[conf_param_name]
    except KeyError:
        help_text = ""

    return HttpResponse(help_text, mimetype = 'text/plain')

def _resource_class_tree(plugin, klass):
    """Resource tree using all instances of 'klass' as origins"""
    records = StorageResourceRecord.objects.filter(
        resource_class__class_name = klass,
        resource_class__storage_plugin__module_name = plugin)
    return _resource_tree(records)

def _resource_tree(root_records):
    from configure.lib.storage_plugin.query import ResourceQuery
    tree = ResourceQuery().get_resource_tree(root_records)

    def decorate_urls(resource_dict):
        from django.core.urlresolvers import reverse
        resource_dict['url'] = reverse('configure.views.storage_resource', kwargs={'srr_id': resource_dict['id']})
        for c in resource_dict['children']:
            decorate_urls(c)

    def decorate_jstree(resource_dict):
        from settings import STATIC_URL
        from django.core.urlresolvers import reverse
        resource_dict['attr'] = {
                'srr_url': "%s" %  reverse('configure.views.storage_resource_inner', kwargs={'srr_id': resource_dict['id']}),
                'srr_id': resource_dict['id']
                }
        resource_dict['data'] = {
                "title": resource_dict['human_string'],
                "icon": "%simages/storage_plugin/%s.png" % (STATIC_URL, resource_dict['icon'])}
        for c in resource_dict['children']:
            decorate_jstree(c)

    class ResourceJsonEncoder(json.JSONEncoder):
        def default(self, o):
            from configure.lib.storage_plugin.resource import StorageResource
            if isinstance(o, StorageResource):
                resource_dict = o.to_json()
                decorate_jstree(resource_dict)
                decorate_urls(resource_dict)
                return resource_dict
            else:
                return super(ResourceJsonEncoder, self).default(o)

    return json.dumps(tree, cls = ResourceJsonEncoder, indent=4)

def storage_browser(request):
    from configure.models import StorageResourceClass
    if StorageResourceClass.objects.count() == 0:
        return render_to_response('storage_browser_disabled.html', RequestContext(request))

    resource_form, storage_resource_class = _handle_resource_form(request)

    storage_plugin = storage_resource_class.storage_plugin
    resource_tree = _resource_class_tree(storage_plugin.module_name, storage_resource_class.class_name)

    return render_to_response('storage_browser.html', RequestContext(request, {
        'resource_form': resource_form,
        'resource_tree': resource_tree
        }))


