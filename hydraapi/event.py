#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from configure.models import ManagedHost
from monitor.models import Event

from requesthandler import AnonymousRESTRequestHandler

from hydraapi.utils import paginate_result


class Handler(AnonymousRESTRequestHandler):
    def get(self, request, host_id = None, severity = None, event_type = None, iDisplayStart = None, iDisplayLength = None, sEcho = None):
        filter_args = []
        filter_kwargs = {}
        if severity:
            filter_kwargs['severity'] = severity
        if host_id:
            host = ManagedHost.objects.get(id=host_id)
            filter_kwargs['host'] = host
        if event_type:
            from django.db.models import Q
            # FIXME: this is a hacky way of filtering by type, should use contenttypes
            filter_args.append(~Q(**{event_type.lower(): None}))

        events = Event.objects.filter(*filter_args, **filter_kwargs).order_by('-created_at')

        def format_fn(event):
            return {
                     'id': event.id,
                     'created_at': event.created_at.strftime("%b %d %H:%M:%S"),
                     'host_name': event.host.pretty_name() if event.host else '',
                     'severity': str(event.severity_class()),
                     'message': event.message()
                   }
        return paginate_result(int(iDisplayStart), int(iDisplayLength), events, format_fn, sEcho)
