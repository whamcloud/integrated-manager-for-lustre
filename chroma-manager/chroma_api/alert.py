#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from collections import defaultdict
from chroma_api.utils import SeverityResource

from django.contrib.contenttypes.models import ContentType
from chroma_core.models.alert import AlertState, AlertSubscription

from tastypie.utils import trailing_slash
from tastypie.resources import Resource, ModelResource
from tastypie import fields
from tastypie.api import url
from tastypie import http
from tastypie.authorization import DjangoAuthorization
from tastypie.validation import Validation
from chroma_api.authentication import AnonymousAuthentication, \
    PATCHSupportDjangoAuth
from chroma_core.models.target import ManagedTargetMount


class AlertSubscriptionValidation(Validation):
    def is_valid(self, bundle, request=None):
        errors = defaultdict(list)

        # Invalid alert_types and nonexistent user_ids will result in 404s,
        # but we should probably protect against non-superusers changing
        # other users' subscriptions. That's a dirty prank.
        import re
        try:
            match = re.search(r'/(\d+)/?$', bundle.data['user'])
            bundle_user_id = match.group(1)
            if not "superusers" in [g.name for g in request.user.groups.all()]:
                if "%s" % bundle_user_id != "%s" % request.user.id:
                    errors['user'].append("Only superusers may change other users' subscriptions.")
        except (KeyError, AttributeError):
            errors['user'].append("Missing or malformed user parameter")

        return errors


class AlertSubscriptionAuthorization(DjangoAuthorization):
    def apply_limits(self, request, object_list):
        if request.method is None:
            # Internal request, it's all good.
            return object_list
        elif not request.user.is_authenticated():
            # Nothing for Anonymous
            return object_list.none()
        elif "superusers" in [g.name for g in request.user.groups.all()]:
            # Superusers can manage other users' subscriptions
            return object_list
        else:
            # Users should only see their own subscriptions
            return object_list.filter(user = request.user)


class AlertSubscriptionResource(ModelResource):
    user = fields.ToOneField("chroma_api.user.UserResource", 'user', help_text="User to which this subscription belongs")
    alert_type = fields.ToOneField("chroma_api.alert.AlertTypeResource", 'alert_type', help_text="Content-type id for this subscription's alert class", full=True)

    class Meta:
        resource_name = "alert_subscription"
        queryset = AlertSubscription.objects.all()
        authorization = AlertSubscriptionAuthorization()
        authentication = AnonymousAuthentication()
        list_allowed_methods = ['get', 'post', 'patch']
        detail_allowed_methods = ['get', 'delete', 'put']
        validation = AlertSubscriptionValidation()


class AlertTypeResource(Resource):
    """
    A list of possible alert types.  Use for
    populating alert subscriptions.
    """
    id = fields.CharField()
    description = fields.CharField()

    def dehydrate_id(self, bundle):
        return str(bundle.obj.id)

    def dehydrate_description(self, bundle):
        def _fixup_alert_name(alert):
            import re
            capitalized = str(alert).capitalize()
            ret = re.sub(r'L net', 'LNet', capitalized)
            return ret

        return _fixup_alert_name(bundle.obj)

    def get_resource_uri(self, bundle_or_obj):
        from tastypie.bundle import Bundle

        kwargs = {
            'resource_name': self._meta.resource_name,
            'api_name': self._meta.api_name
        }

        if isinstance(bundle_or_obj, Bundle):
            kwargs['pk'] = bundle_or_obj.obj.id
        else:
            kwargs['pk'] = bundle_or_obj.id

        return self._build_reverse_url("api_dispatch_detail", kwargs=kwargs)

    def get_object_list(self, request):
        return [ContentType.objects.get_for_model(cls)
                for cls in AlertState.subclasses()]

    def obj_get_list(self, request=None, **kwargs):
        return self.get_object_list(request)

    def obj_get(self, request=None, **kwargs):
        return ContentType.objects.get(pk=kwargs['pk'])

    class Meta:
        resource_name = 'alert_type'
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']


class AlertResource(SeverityResource):
    """
    Notification of a bad health state.  Alerts refer to particular objects (such as
    servers or targets), and can either be active (indicating this is a current
    problem) or inactive (indicating this is a historical record of a problem).

    The ``alert_item_content_type_id`` and ``alert_item_id`` attributes
    together provide a unique reference to the object to which the
    alert refers.
    """

    message = fields.CharField(readonly = True,
        help_text = ("Human readable description "
                     "of the alert, about one sentence"))

    alert_item_content_type_id = fields.IntegerField(attribute = 'alert_item_type_id',
        help_text = "Content type ID of affected item")

    alert_item_id = fields.IntegerField(attribute = 'alert_item_id',
        help_text = "ID of affected item")

    alert_item = fields.CharField(help_text = "URI of affected item")

    alert_type = fields.CharField(attribute = 'alert_type',
        help_text = "The type of alert, which is the name of class for the alert. Ex: 'HostOfflineAlert'")

    active = fields.BooleanField(attribute = 'active_bool', null = True,
        help_text = "``true`` if the alert is a current issue, "
                    "``false`` if it is historical")

    affected = fields.ListField(null = True,
        help_text = ("List of objects which are affected by the alert "
                     "(e.g. a target alert also affects the file system to "
                     "which the target belongs)"))

    alert_item_str = fields.CharField(readonly = True,
        help_text = ("A human readable noun describing the object "
                     "that is the subject of the alert"))

    # This addition is because when we are querying notifications it is useful to be able query by created_at
    # begin is clearly the best analogy
    created_at = fields.DateTimeField(readonly = True, attribute = 'begin')

    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/dismiss_all%s$' % (self._meta.resource_name, trailing_slash()), self.wrap_view('dismiss_all'), name='api_alert_dismiss_all'),
        ]

    def dismiss_all(self, request, **kwargs):
        if (request.method != 'PUT') or (not request.user.is_authenticated()):
            return http.HttpUnauthorized()

        AlertState.objects.filter(dismissed = False).exclude(active = True, severity__in = [40, 30]).update(dismissed = True)

        return http.HttpNoContent()

    def dehydrate_alert_item(self, bundle):
        from chroma_api.urls import api
        return api.get_resource_uri(bundle.obj.alert_item)

    def dehydrate_alert_item_str(self, bundle):
        return str(bundle.obj.alert_item)

    def dehydrate_message(self, bundle):
        return bundle.obj.message()

    def dehydrate_affected(self, bundle):
        from chroma_api.urls import api

        # FIXME: really don't want to call this every time someone gets a list of alerts
        # >> FIXME HYD-421 Hack: this info should be provided in a more generic way by
        #    AlertState subclasses
        # NB adding a 'what_do_i_affect' method to
        a = bundle.obj.downcast()

        affected_objects = set()

        from chroma_core.models import StorageResourceAlert, StorageAlertPropagated
        from chroma_core.models import Volume
        from chroma_core.models import ManagedMgs
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
            luns = Volume.objects.filter(storage_resource__in = affected_srrs)
            for l in luns:
                for ln in l.volumenode_set.all():
                    tms = ManagedTargetMount.objects.filter(volume_node = ln)
                    for tm in tms:
                        affect_target(tm.target)
        elif isinstance(a, TargetFailoverAlert):
            affect_target(a.alert_item)
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

        filters = super(AlertResource, self).build_filters(filters)

        # Map False to None and 'active_bool' to 'active'
        if 'active_bool__exact' in filters:
            filters['active__exact'] = None if not filters['active_bool__exact'] else True
            del filters['active_bool__exact']

        return filters

    class Meta:
        queryset = AlertState.objects.all()
        resource_name = 'alert'
        fields = ['begin', 'end', 'message', 'active', 'dismissed',
                  'alert_item_id', 'alert_item_content_type_id', 'id',
                  'severity', 'alert_type', 'created_at']
        filtering = {'active': ['exact'],
                     'dismissed': ['exact'],
                     'severity': ['in', 'exact'],
                     'begin': ['gte'],
                     'alert_type': ['exact', 'in'],
                     'alert_item_id': ['exact', 'in'],
                     'alert_item_content_type_id': ['exact', 'in'],
                     'created_at': ['gte', 'lte', 'gt', 'lt']}
        ordering = ['begin', 'end', 'active']
        authorization = PATCHSupportDjangoAuth()
        authentication = AnonymousAuthentication()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get', 'patch', 'put']
        always_return_data = True
