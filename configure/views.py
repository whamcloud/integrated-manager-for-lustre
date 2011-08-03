
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseBadRequest
from django import forms

from monitor.models import *
from configure.models import *

# IMPORTANT
# These views are implicitly transactions.  If you create an object and then 
# submit a celery job that does something to it, the job could execute before
# the transaction is committed, and fail because the object doesn't exist.
# We hopefully don't have that problem with the djkombu backend (it's all going into
# the same database, but bear it in mind!

def setup(request):
    can_create_mdt = (MetadataTarget.objects.count() != Filesystem.objects.count())

    return render_to_response("setup.html", RequestContext(request, {
        'mgss': ManagementTarget.objects.all(),
        'filesystems': Filesystem.objects.all(),
        'hosts': Host.objects.all(),
        'can_create_mdt': can_create_mdt
        }))

def _create_target_mounts(node, target, failover_host = None):
    tm = ManagedTargetMount(
        block_device = node,
        target = target,
        host = node.host, 
        mount_point = target.default_mount_path(node.host),
        primary = True)
    tm.save()

    if failover_host:
        tm = ManagedTargetMount(
            block_device = None,
            target = target,
            host = failover_host, 
            mount_point = target.default_mount_path(failoverhost),
            primary = False)
        tm.save()

def create_mgs(request, host_id):
    host = get_object_or_404(Host, id = int(host_id))
    # TODO: some UI for forcing it to accept a node which has used_hint=True
    nodes = LunNode.objects.filter(host = host, used_hint = False) 
    other_hosts = [h for h in Host.objects.all() if h != host]

    class CreateMgsForm(forms.Form):
        device = forms.ChoiceField(choices = [(n.id, n.path) for n in nodes])
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
            _create_target_mounts(node, target, failover_host)

            return redirect('configure.views.setup')

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
            fs = Filesystem(mgs = mgs, name = form.cleaned_data['name'])
            fs.save()
            return redirect('configure.views.setup')
    else:
        return HttpResponseBadRequest

    return render_to_response("create_fs.html", RequestContext(request, {
        'mgs': mgs,
        'form': form
        }))

def create_oss(request, host_id):
    host = get_object_or_404(Host, id = int(host_id))
    # TODO: some UI for forcing it to accept a node which has used_hint=True
    nodes = host.available_lun_nodes()
    other_hosts = [h for h in Host.objects.all() if h != host]

    class CreateOssForm(forms.Form):
        filesystem = forms.ChoiceField(choices = [(f.id, f.name) for f in Filesystem.objects.all()])
        failover_partner = forms.ChoiceField(choices = [(None, 'None')] + [(h.id, h) for h in other_hosts])

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
                'node_name': node.path,
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
            filesystem = Filesystem.objects.get(id=form.cleaned_data['filesystem'])

            for node_form in node_forms:
                if node_form.cleaned_data['use']:
                    node = node_form.node

                    ost = ManagedOst(filesystem = filesystem)
                    ost.save()
                    _create_target_mounts(node, ost, failover_host)

            return redirect('configure.views.setup')
    else:
        return HttpResponseBadRequest

    return render_to_response("create_oss.html", RequestContext(request, {
        'host': host,
        'form': form,
        'node_forms': node_forms
        }))

def create_mds(request, host_id):
    host = get_object_or_404(Host, id = int(host_id))
    # TODO: some UI for forcing it to accept a node which has used_hint=True
    nodes = host.available_lun_nodes()
    other_hosts = [h for h in Host.objects.all() if h != host]

    filesystems_with_mdt = [mdt.filesystem for mdt in MetadataTarget.objects.all()]
    filesystems = [f for f in Filesystem.objects.all() if not f in filesystems_with_mdt]

    class CreateMdtForm(forms.Form):
        filesystem = forms.ChoiceField(choices = [(f.id, f.name) for f in filesystems])
        device = forms.ChoiceField(choices = [(n.id, n.path) for n in nodes])
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
            filesystem = Filesystem.objects.get(id=form.cleaned_data['filesystem'])

            target = ManagedMdt(filesystem = filesystem)
            target.save()
            _create_target_mounts(node, target, failover_host)

            return redirect('configure.views.setup')

    else:
        return HttpResponseBadRequest

    return render_to_response("create_mds.html", RequestContext(request, {
        'host': host,
        'form': form
        }))

def jobs(request):
    return render_to_response("jobs.html", RequestContext(request, {
        'jobs': JobRecord.objects.all()
        }))

def job(request, job_id):
    job = get_object_or_404(JobRecord, id = job_id)
    return render_to_response("job.html", RequestContext(request, {
        'job': job
        }))

def states(request):
    klasses = [ManagedTarget, ManagedHost, ManagedTargetMount]
    items = []
    for klass in klasses:
        items.extend(list(klass.objects.all()))

    return render_to_response("states.html", RequestContext(request, {
        'stateful_objects': items
        }))

