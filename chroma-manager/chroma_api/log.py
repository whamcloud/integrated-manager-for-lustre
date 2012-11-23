#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from tastypie import fields

from chroma_core.models.log import Systemevents

from tastypie.resources import ModelResource
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication


class LogAuthorization(DjangoAuthorization):
    """
    custom authorization class for log retrieval

    Only users in the superusers and filesystem_administrators groups are
    allowed to retrieve non-Lustre messages
    """
    def apply_limits(self, request, object_list):
        if (request.user.is_authenticated() and
            request.user.groups.filter(name__in=['filesystem_administrators', 'superusers']).exists()):
            return object_list
        else:
            # Lustre messages have a leading space
            return object_list.filter(message__startswith=u' Lustre')


class LogResource(ModelResource):
    """
    syslog messages collected by Chroma server.  The fields in this table
    correspond to the default ``rsyslog`` MySQL output.

    You are probably mainly interested in ``fromhost``, ``devicereportedtime`` and
    ``message``.  Note that ``fromhost`` is a hostname rather than a reference to
    the ``host`` resource -- it is not guaranteed that a host mentioned in the
    syslog is configured as a host in Chroma server.
    """
    substitutions = fields.ListField(null = True, help_text = """List of dictionaries describing
substrings which may be used to decorate the `message` attribute with hyperlinks.  Each substitution
has `start`, `end`, `label` and `resource_uri` attributes.""")

    def dehydrate_substitutions(self, bundle):
        return self._substitutions(bundle.obj)

    class Meta:
        queryset = Systemevents.objects.all()
        filtering = {
                'severity': ['exact'],
                'fromhost': ['exact', 'startswith'],
                'devicereportedtime': ['gte', 'lte'],
                'message': ['icontains', 'startswith', 'contains'],
                }
        authorization = LogAuthorization()
        authentication = AnonymousAuthentication()
        ordering = ['devicereportedtime', 'fromhost']
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']

    def build_filters(self, filters = None):
        # TODO: let the UI filter on nodename to avoid the need for this mangling
        host_id = filters.get('host_id', None)
        if host_id:
            del filters['host_id']
            from chroma_core.models import ManagedHost
            host = ManagedHost.objects.get(id=host_id)
            filters['fromhost'] = host.fqdn

        return super(LogResource, self).build_filters(filters)

    def _substitutions(self, obj):
        message = obj.message
        from chroma_api import api_log
        from chroma_api.urls import api

        from chroma_core.models import ManagedHost, ManagedTarget
        from chroma_core.lib.lustre_audit import normalize_nid
        import re

        substitutions = []

        def substitute(object, match, group = 1):
            resource_uri = api.get_resource_uri(object)
            substitutions.append({
                'start': match.start(group),
                'end': match.end(group),
                'label': object.get_label(),
                'resource_uri': resource_uri})

        # TODO: detect other NID types (cray?)
        nid_regex = re.compile("(\d{1,3}\.){3}\d{1,3}@(tcp|ib)(_\d+)?")
        target_regex = re.compile("[^\w](\w{1,8}-(MDT|OST)[\da-f]{4})")
        for match in nid_regex.finditer(message):
            nid = match.group(0)
            nid = normalize_nid(nid)
            try:
                host = ManagedHost.get_by_nid(nid)
            except ManagedHost.DoesNotExist:
                api_log.warn("No host has NID %s" % nid)
                continue
            except ManagedHost.MultipleObjectsReturned:
                api_log.warn("Multiple hosts have NID %s" % nid)
                continue
            if host.state != 'removed':
                substitute(host, match, 0)

        for match in target_regex.finditer(message):
            target_name = match.group(1)
            for target in ManagedTarget.objects.filter(name=target_name)[:1]:
                substitute(target, match)

        return sorted(substitutions, key=lambda sub: sub['start'])
