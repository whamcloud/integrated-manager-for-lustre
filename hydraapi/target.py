#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.core.management import setup_environ
from django.shortcuts import get_object_or_404
import settings
setup_environ(settings)

from configure.lib.state_manager import StateManager

from configure.models import ManagedOst, ManagedMdt, ManagedMgs, ManagedTargetMount, ManagedTarget
from requesthandler import AnonymousRESTRequestHandler

KIND_TO_KLASS = {"MGT": ManagedMgs,
            "OST": ManagedOst,
            "MDT": ManagedMdt}
KLASS_TO_KIND = dict([(v, k) for k, v in KIND_TO_KLASS.items()])


class TargetHandler(AnonymousRESTRequestHandler):
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
