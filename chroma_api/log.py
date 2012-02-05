#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.models import ManagedHost
from chroma_core.models import Systemevents

from hydraapi.requesthandler import RequestHandler

from chroma_api.utils import paginate_result

import datetime


class Handler(RequestHandler):
    def get(self, request, host_id = None, start_time = None, end_time = None,
        lustre = False, iDisplayStart = None, iDisplayLength = None, sSearch = None):

        if sSearch:
            sSearch = sSearch.encode('utf-8')
        if iDisplayStart:
            iDisplayStart = int(iDisplayStart)
        if iDisplayLength:
            iDisplayLength = int(iDisplayLength)

        ui_time_format = "%m/%d/%Y %H:%M "
        filter_kwargs = {}
        if start_time:
            start_date = datetime.datetime.strptime(str(start_time), ui_time_format)
            filter_kwargs['devicereportedtime__gte'] = start_date
        if end_time:
            end_date = datetime.datetime.strptime(str(end_time), ui_time_format)
            filter_kwargs['devicereportedtime__lte'] = end_date
        if host_id:
            host = ManagedHost.objects.get(id=host_id)
            # FIXME: use nodename here once it's in
            filter_kwargs['fromhost__startswith'] = host.pretty_name()
        if lustre == 'true':
            filter_kwargs['message__startswith'] = " Lustre"
        if sSearch:
            filter_kwargs['message__icontains'] = sSearch

        def log_class(log_entry):
            if log_entry.message.find('LustreError') != -1:
                return 'log_error'
            else:
                return 'log_info'

        def format_fn(systemevent_record):
            return {
                    'id': systemevent_record.id,
                    'message': nid_finder(systemevent_record.message),
                    # Trim trailing colon from e.g. 'kernel:'
                    'service': systemevent_record.syslogtag.rstrip(":"),
                    'date': systemevent_record.devicereportedtime.strftime("%b %d %H:%M:%S"),
                    'host': systemevent_record.fromhost,
                    'DT_RowClass': log_class(systemevent_record)
                       }

        log_data = Systemevents.objects.filter(**filter_kwargs).order_by('-devicereportedtime')
        return paginate_result(iDisplayStart, iDisplayLength, log_data, format_fn)


def nid_finder(message):
    from chroma_api import api_log

    from chroma_core.models import ManagedHost, ManagedTarget
    from chroma_core.lib.lustre_audit import normalize_nid
    import re
    # TODO: detect IB/other(cray?) as well as tcp
    nid_regex = re.compile("(\d{1,3}\.){3}\d{1,3}@tcp(_\d+)?")
    target_regex = re.compile("\\b(\\w+-(MDT|OST)\\d\\d\\d\\d)\\b")
    for match in nid_regex.finditer(message):
        replace = match.group()
        replace = normalize_nid(replace)
        try:
            host = ManagedHost.get_by_nid(replace)
        except ManagedHost.DoesNotExist:
            api_log.warn("No host has NID %s" % replace)
            continue
        except ManagedHost.MultipleObjectsReturned:
            api_log.warn("Multiple hosts have NID %s" % replace)
            continue

        markup = "<a href='#' title='%s'>%s</a>" % (match.group(), host.address)
        message = message.replace(match.group(),
                                  markup)
    for match in target_regex.finditer(message):
        # TODO: look up to a target and link to something useful
        replace = match.group()
        #markup = "<a href='#' title='%s'>%s</a>" % ("foo", match.group())
        markup = match.group()
        try:
            t = ManagedTarget.objects.get(name=markup)
            markup = "<a href='#' class='target target_id_%s'>%s</a>" % (t.id, t.get_label())
        except:
            pass
        message = message.replace(match.group(),
                                  markup,
                                  1)
    return message
