#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import datetime

from chroma_core.models.log import Systemevents

from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication


class LogResource(ModelResource):
    host_name = fields.CharField()
    service = fields.CharField()
    date = fields.DateTimeField()

    def dehydrate_message(self, bundle):
        return nid_finder(bundle.obj.message)

    class Meta:
        queryset = Systemevents.objects.all()
        exclude = ['syslogtag', 'devicereportedtime', 'fromhost']
        filtering = {
                'severity': ['exact'],
                'fromhost': ['exact', 'startswith'],
                'devicereportedtime': ['gte', 'lte'],
                'message': ['icontains', 'startswith'],
                }
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()

    def build_filters(self, filters = None):
        # FIXME: get the UI to give us ISO8601 so that we
        # can let tastypie use it without mangling
        # TODO: document the expected time format in this call
        UI_TIME_FORMAT = "%m/%d/%Y %H:%M "
        start = filters.get('devicereportedtime_gte', None)
        if start:
            filters['devicereportedtime_gte'] = datetime.datetime.strptime(str(start), UI_TIME_FORMAT)
        end = filters.get('devicereportedtime_lte', None)
        if end:
            filters['devicereportedtime_lte'] = datetime.datetime.strptime(str(end), UI_TIME_FORMAT)

        # TODO: let the UI filter on nodename to avoid the need for this mangling
        host_id = filters.get('host_id', None)
        if host_id:
            del filters['host_id']
            from chroma_core.models import ManagedHost
            host = ManagedHost.objects.get(id=host_id)
            filters['fromhost__startswith'] = host.pretty_name()

        return super(LogResource, self).build_filters(filters)


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
