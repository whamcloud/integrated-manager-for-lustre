#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.lib.util import normalize_nid

from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.authorization import DjangoAuthorization

from chroma_api.authentication import AnonymousAuthentication
from chroma_core.models.log import LogMessage, MessageClass


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
            return object_list.filter(message_class__in = [MessageClass.LUSTRE, MessageClass.LUSTRE_ERROR])


class LogResource(ModelResource):
    """
    syslog messages collected by the Command Center.



    """
    substitutions = fields.ListField(null = True, help_text = """List of dictionaries describing \
substrings which may be used to decorate the `message` attribute by adding hyperlinks.  Each substitution \
has `start`, `end`, `label` and `resource_uri` attributes.""")

    message_class = fields.CharField(attribute = 'message_class', help_text = "Unicode string.  One of %s" % MessageClass.strings())

    def dehydrate_substitutions(self, bundle):
        return self._substitutions(bundle.obj)

    class Meta:
        queryset = LogMessage.objects.all()
        filtering = {
            'fqdn': ['exact', 'startswith'],
            'datetime': ['gte', 'lte'],
            'message': ['icontains', 'startswith', 'contains'],
            'message_class': ['in', 'exact']
        }

        authorization = LogAuthorization()
        authentication = AnonymousAuthentication()
        ordering = ['datetime', 'fqdn']
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']

    def dehydrate_message_class(self, bundle):
        return MessageClass.to_string(bundle.obj.message_class)

    def build_filters(self, filters = None):
        # TODO: make the UI filter on FQDN to avoid the need for this mangling
        host_id = filters.get('host_id', None)
        if host_id is not None:
            del filters['host_id']
            from chroma_core.models import ManagedHost
            host = ManagedHost.objects.get(id=host_id)
            filters['fqdn'] = host.fqdn

        if 'message_class__in' in filters:
            filters.setlist('message_class__in', [MessageClass.from_string(s).__str__() for s in filters.getlist('message_class__in')])

        if 'message_class' in filters:
            filters['message_class'] = MessageClass.from_string(filters['message_class'])

        return super(LogResource, self).build_filters(filters)

    def _substitutions(self, obj):
        message = obj.message
        from chroma_api import api_log
        from chroma_api.urls import api

        from chroma_core.models import ManagedHost, ManagedTarget
        import re

        substitutions = []

        def substitute(obj, match, group = 1):
            resource_uri = api.get_resource_uri(obj)
            substitutions.append({
                'start': match.start(group),
                'end': match.end(group),
                'label': obj.get_label(),
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
