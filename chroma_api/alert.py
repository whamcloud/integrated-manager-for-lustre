# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import defaultdict
from chroma_api.utils import SeverityResource, DateSerializer

from django.contrib.contenttypes.models import ContentType
from chroma_core.models.alert import AlertState
from chroma_core.models.alert import AlertStateBase
from chroma_core.models.alert import AlertSubscription
from chroma_core.models.utils import STR_TO_SEVERITY

from tastypie.utils import trailing_slash
from tastypie.resources import Resource
from tastypie import fields
from tastypie.api import url
from tastypie import http
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.validation import Validation
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.chroma_model_resource import ChromaModelResource
from iml_common.lib import util


class AlertSubscriptionValidation(Validation):
    def is_valid(self, bundle, request=None):
        errors = defaultdict(list)

        # Invalid alert_types and nonexistent user_ids will result in 404s,
        # but we should probably protect against non-superusers changing
        # other users' subscriptions. That's a dirty prank.
        import re

        try:
            match = re.search(r"/(\d+)/?$", bundle.data["user"])
            bundle_user_id = match.group(1)
            if not "superusers" in [g.name for g in request.user.groups.all()]:
                if "%s" % bundle_user_id != "%s" % request.user.id:
                    errors["user"].append("Only superusers may change other users' subscriptions.")
        except (KeyError, AttributeError):
            errors["user"].append("Missing or malformed user parameter")

        return errors


class AlertSubscriptionAuthorization(PatchedDjangoAuthorization):
    def read_list(self, object_list, bundle):
        request = bundle.request
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
            return object_list.filter(user=request.user)


class AlertSubscriptionResource(ChromaModelResource):
    user = fields.ToOneField(
        "chroma_api.user.UserResource", "user", help_text="User to which this subscription belongs"
    )
    alert_type = fields.ToOneField(
        "chroma_api.alert.AlertTypeResource",
        "alert_type",
        help_text="Content-type id for this subscription's alert class",
        full=True,
    )

    class Meta:
        resource_name = "alert_subscription"
        queryset = AlertSubscription.objects.all()
        authorization = AlertSubscriptionAuthorization()
        authentication = AnonymousAuthentication()
        list_allowed_methods = ["get", "post", "patch"]
        detail_allowed_methods = ["get", "delete", "put"]
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
            ret = re.sub(r"L net", "LNet", capitalized)
            return ret

        return _fixup_alert_name(bundle.obj)

    def get_resource_uri(self, bundle_or_obj=None):
        from tastypie.bundle import Bundle

        url_name = "api_dispatch_list"

        if bundle_or_obj is not None:
            url_name = "api_dispatch_detail"

        kwargs = {"resource_name": self._meta.resource_name, "api_name": self._meta.api_name}

        if isinstance(bundle_or_obj, Bundle):
            kwargs["pk"] = bundle_or_obj.obj.id
        elif bundle_or_obj is not None:
            kwargs["pk"] = bundle_or_obj.id

        return self._build_reverse_url(url_name, kwargs=kwargs)

    def get_object_list(self, request):
        return [
            ContentType.objects.get_for_model(cls, False)
            for cls in AlertStateBase.subclasses()
            if cls is not AlertState
        ]

    def obj_get_list(self, bundle, **kwargs):
        return self.get_object_list(bundle.request)

    def obj_get(self, bundle, **kwargs):
        return ContentType.objects.get(pk=kwargs["pk"])

    class Meta:
        resource_name = "alert_type"
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        list_allowed_methods = ["get"]
        detail_allowed_methods = ["get"]


class AlertResource(SeverityResource):
    """
    Notification of a bad health state.  Alerts refer to particular objects (such as
    servers or targets), and can either be active (indicating this is a current
    problem) or inactive (indicating this is a historical record of a problem).
    """

    message = fields.CharField(
        readonly=True, help_text=("Human readable description " "of the alert, about one sentence")
    )

    alert_item = fields.CharField(help_text="URI of affected item")

    affected = fields.ListField(
        null=True,
        help_text=(
            "List of objects which are affected by the alert "
            "(e.g. a target alert also affects the file system to "
            "which the target belongs)"
        ),
    )

    affected_composite_ids = fields.ListField(
        help_text=(
            "List of composite ids which are affected by the alert "
            "(e.g. a target alert also affects the file system to "
            "which the target belongs)"
        ),
    )

    alert_item_str = fields.CharField(
        readonly=True, help_text=("A human readable noun describing the object " "that is the subject of the alert")
    )

    record_type = fields.CharField(
        attribute="record_type",
        help_text="The type of the alert described as a Python classes",
        enumerations=[class_.__name__ for class_ in util.all_subclasses(AlertStateBase)],
    )

    severity = fields.CharField(
        attribute="severity",
        help_text=("String indicating the " "severity of the alert, " "one of %s") % STR_TO_SEVERITY.keys(),
        enumerations=STR_TO_SEVERITY.keys(),
    )

    def prepend_urls(self):
        return [
            url(
                r"^(?P<resource_name>%s)/dismiss_all%s$" % (self._meta.resource_name, trailing_slash()),
                self.wrap_view("dismiss_all"),
                name="api_alert_dismiss_all",
            )
        ]

    def dismiss_all(self, request, **kwargs):
        if (request.method != "PUT") or (not request.user.is_authenticated()):
            return http.HttpUnauthorized()

        AlertState.objects.filter(dismissed=False).exclude(active=True, severity__in=[40, 30]).update(dismissed=True)

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

        alert = bundle.obj

        affected_objects = []

        def affect_target(target):
            affected_objects.append(target)
            if target.filesystem_member:
                affected_objects.append(target.filesystem)
            elif target.target_type == "mgs":
                for fs in target.managedfilesystem_set.all():
                    affected_objects.append(fs)

        affected_objects.extend(alert.affected_objects)

        alert.affected_targets(affect_target)

        affected_objects.append(alert.alert_item)

        return [api.get_resource_uri(ao) for ao in set(affected_objects)]

    def dehydrate_affected_composite_ids(self, bundle):
        alert = bundle.obj

        affected_objects = []

        def affect_target(target):
            affected_objects.append(target)
            if target.filesystem_member:
                affected_objects.append(target.filesystem)
            elif target.target_type == "mgs":
                for fs in target.managedfilesystem_set.all():
                    affected_objects.append(fs)

        affected_objects.extend(alert.affected_objects)

        alert.affected_targets(affect_target)

        affected_objects.append(alert.alert_item)

        def build_composite_id(x):
            if getattr(x, "downcast", None) and callable(x.downcast):
                item = x.downcast()
            else:
                item = x

            content_type_id = ContentType.objects.get_for_model(item).id

            return "{}:{}".format(content_type_id, item.id)

        return [build_composite_id(x) for x in set(affected_objects)]

    def build_filters(self, filters=None, **kwargs):

        filters = super(AlertResource, self).build_filters(filters)

        # Map False to None and 'active_bool' to 'active'
        if "active_bool__exact" in filters:
            filters["active__exact"] = None if not filters["active_bool__exact"] else True
            del filters["active_bool__exact"]

        return filters

    class Meta:
        queryset = AlertState.objects.order_by("-begin")
        resource_name = "alert"

        filtering = {
            "begin": SeverityResource.ALL_FILTER_DATE,
            "end": SeverityResource.ALL_FILTER_DATE,
            "message": SeverityResource.ALL_FILTER_STR,
            "active": SeverityResource.ALL_FILTER_BOOL,
            "dismissed": SeverityResource.ALL_FILTER_BOOL,
            "id": SeverityResource.ALL_FILTER_INT,
            "severity": SeverityResource.ALL_FILTER_ENUMERATION,
            "created_at": SeverityResource.ALL_FILTER_DATE,
            "alert_type": SeverityResource.ALL_FILTER_ENUMERATION,
            "alert_item_id": SeverityResource.ALL_FILTER_INT,
            "lustre_pid": SeverityResource.ALL_FILTER_INT,
            "record_type": SeverityResource.ALL_FILTER_ENUMERATION,
        }

        ordering = ["begin", "end", "active"]
        serializer = DateSerializer()
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        list_allowed_methods = ["get"]
        detail_allowed_methods = ["get", "patch", "put"]
        always_return_data = True
