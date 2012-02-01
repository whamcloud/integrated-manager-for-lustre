#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.shortcuts import get_object_or_404

from django.db import transaction

from configure.lib.state_manager import StateManager

from configure.models import ManagedOst, ManagedMdt, ManagedMgs, ManagedTargetMount, ManagedTarget, ManagedFilesystem, Lun
from hydraapi.requesthandler import AnonymousRESTRequestHandler, APIResponse
import configure.lib.conf_param

from configure.models import Command


KIND_TO_KLASS = {"MGT": ManagedMgs,
            "OST": ManagedOst,
            "MDT": ManagedMdt}
KLASS_TO_KIND = dict([(v, k) for k, v in KIND_TO_KLASS.items()])


def create_target(lun_id, target_klass, **kwargs):
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


class TargetHandler(AnonymousRESTRequestHandler):
    def put(self, request, id):
        target = get_object_or_404(ManagedTarget, pk = id).downcast()
        try:
            conf_params = request.data['conf_params']
        except KeyError:
            return APIResponse(None, 400)

        # TODO: validate the parameters before trying to set any of them

        for k, v in conf_params.items():
            configure.lib.conf_param.set_conf_param(target, k, v)

    def post(self, request, kind, filesystem_id = None, lun_ids = []):
        if not kind in KIND_TO_KLASS:
            return APIResponse(None, 400)

        # TODO: define convention for API errors, and put some
        # helpful messages in here
        # Cannot specify a filesystem to which an MGT should belong
        if kind == "MGT" and filesystem_id:
            return APIResponse(None, 400)

        # Cannot create MDTs with this call (it is done in filesystem creation)
        if kind == "MDT":
            return APIResponse(None, 400)

        # Need at least one LUN
        if len(lun_ids) < 1:
            return APIResponse(None, 400)

        if kind == "OST":
            fs = ManagedFilesystem.objects.get(id=filesystem_id)
            create_kwargs = {'filesystem': fs}
        elif kind == "MGT":
            create_kwargs = {'name': 'MGS'}

        targets = []
        with transaction.commit_on_success():
            for lun_id in lun_ids:
                targets.append(create_target(lun_id, KIND_TO_KLASS[kind], **create_kwargs))

        message = "Creating %s" % kind
        if len(lun_ids) > 1:
            message += "s"

        with transaction.commit_on_success():
            command = Command(message = "Creating OSTs")
            command.save()
        for target in targets:
            StateManager.set_state(target, 'mounted', command.pk)
        return APIResponse(command.to_dict(), 202)

    def get(self, request, id = None, host_id = None, filesystem_id = None, kind = None):
        if id:
            target = get_object_or_404(ManagedTarget, pk = id).downcast()
            return target.to_dict()
        else:
            targets = []

            # Apply kind filter
            if kind:
                klasses = [KIND_TO_KLASS[kind]]
            else:
                klasses = [ManagedMgs, ManagedMdt, ManagedOst]

            for klass in klasses:
                filter_kwargs = {}
                if klass == ManagedMgs and filesystem_id:
                    # For MGT, filesystem_id filters on the filesystem belonging to the MGT
                    filter_kwargs['managedfilesystem__id'] = filesystem_id
                elif klass != ManagedMgs and filesystem_id:
                    # For non-MGT, filesystem_id filters on the target belonging to the filesystem
                    filter_kwargs['filesystem__id'] = filesystem_id

                for t in klass.objects.filter(**filter_kwargs):
                    # Apply host filter
                    # FIXME: this filter should be done with a query instead of in a loop
                    if host_id and ManagedTargetMount.objects.filter(target = t, host__id = host_id).count() == 0:
                        continue
                    else:
                        d = t.to_dict()
                        d['available_transitions'] = StateManager.available_transitions(t)
                        targets.append(d)
            return targets
