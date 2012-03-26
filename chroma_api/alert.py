#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.contrib.contenttypes.models import ContentType
from chroma_core.models.alert import AlertState

from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication


class AlertResource(ModelResource):
    """
    A bad health state.  Alerts refer to particular objects (such as
    servers or targets), and can either be active (this is a current
    problem) or inactive (this is a historical record of a problem).

    The ``alert_item_content_type_id`` and ``alert_item_id`` attributes
    together provide a unique reference to the object to which the
    alert refers.
    """
    message = fields.CharField(readonly = True, help_text = "Human readable description\
            of the alert, about one sentence")
    alert_item_content_type_id = fields.IntegerField()
    active = fields.BooleanField(attribute = 'active', null = True,
            help_text = "True if the alert is a current issue, false\
            if it is historical")

    affected = fields.ListField(null = True, help_text = "List of objects which\
            are affected by the alert (e.g. a target alert also affects the\
            filesystem to which the target belongs)")

    def dehydrate_affected(self, bundle):
        from chroma_api.urls import api

        # FIXME: really don't want to call this every time someone gets a list of alerts
        # >> FIXME HYD-421 Hack: this info should be provided in a more generic way by
        #    AlertState subclasses
        # NB adding a 'what_do_i_affect' method to
        a = bundle.obj.downcast()

        affected_objects = set()

        from chroma_core.models import StorageResourceAlert, StorageAlertPropagated
        from chroma_core.models import Lun
        from chroma_core.models import ManagedTargetMount, ManagedMgs
        from chroma_core.models import FilesystemMember
        from chroma_core.models import TargetOfflineAlert, TargetRecoveryAlert, TargetFailoverAlert, HostContactAlert

        def affect_target(target):
            target = target.downcast()
            affected_objects.add(target)
            if isinstance(target, FilesystemMember):
                affected_objects.add(target.filesystem)
            elif isinstance(target, ManagedMgs):
                for fs in target.managedfilesystem_set.all():
                    affected_objects.add(fs)

        if isinstance(a, StorageResourceAlert):
            affected_srrs = [sap['storage_resource_id'] for sap in StorageAlertPropagated.objects.filter(alert_state = a).values('storage_resource_id')]
            affected_srrs.append(a.alert_item_id)
            luns = Lun.objects.filter(storage_resource__in = affected_srrs)
            for l in luns:
                for ln in l.lunnode_set.all():
                    tms = ManagedTargetMount.objects.filter(block_device = ln)
                    for tm in tms:
                        affect_target(tm.target)
        elif isinstance(a, TargetFailoverAlert):
            affect_target(a.alert_item.target)
        elif isinstance(a, TargetOfflineAlert) or isinstance(a, TargetRecoveryAlert):
            affect_target(a.alert_item)
        elif isinstance(a, HostContactAlert):
            tms = ManagedTargetMount.objects.filter(host = a.alert_item)
            for tm in tms:
                affect_target(tm.target)

        result = []
        affected_objects.add(a.alert_item)
        for ao in affected_objects:
            ct = ContentType.objects.get_for_model(ao)
            result.append({
                "id": ao.pk,
                "content_type_id": ct.pk,
                "resource_uri": api.get_resource_uri(ao)
                })

        return result
        # <<

    def build_filters(self, filters = None):
        # Map False to None for ``active`` field
        filters = super(AlertResource, self).build_filters(filters)
        if 'active__exact' in filters:
            if not filters['active__exact']:
                filters['active__exact'] = None
        return filters

    def dehydrate_active(self, bundle):
        # Map False to None for ``active`` field
        return bool(bundle.obj.active)

    def dehydrate_alert_item_content_type_id(self, bundle):
        return bundle.obj.alert_item_type.id

    alert_item_str = fields.CharField(readonly = True,
            help_text = "A human readable noun describing the object\
            that is the subject of the alert")

    class Meta:
        queryset = AlertState.objects.all()
        resource_name = 'alert'
        fields = ['begin', 'end', 'message', 'active', 'alert_item_id', 'alert_item_content_type_id', 'id']
        filtering = {'active': ['exact']}
        ordering = ['begin', 'end', 'active']
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']

    def dehydrate_message(self, bundle):
        return bundle.obj.message()

    def dehydrate_alert_item_str(self, bundle):
        return str(bundle.obj.alert_item)
