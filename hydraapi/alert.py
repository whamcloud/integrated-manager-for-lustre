#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydraapi.requesthandler import RequestHandler

from hydraapi.utils import paginate_result


class Handler(RequestHandler):
    def get(self, request, active = None, iDisplayStart = None, iDisplayLength = None, sEcho = None):
        from monitor.models import AlertState
        if active:
            active = True
        else:
            active = None
        alerts = AlertState.objects.filter(active = active).order_by('end')

        def format_fn(alert):
            return alert.to_dict()

        if iDisplayStart:
            iDisplayStart = int(iDisplayStart)
        if iDisplayLength:
            iDisplayLength = int(iDisplayLength)

        return paginate_result(iDisplayStart, iDisplayLength, alerts, format_fn, sEcho)
