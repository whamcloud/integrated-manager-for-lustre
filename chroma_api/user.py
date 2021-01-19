# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from tastypie.bundle import Bundle
from tastypie import fields
from tastypie.validation import Validation
from tastypie.http import HttpBadRequest

from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.chroma_model_resource import ChromaModelResource


class ChromaUserChangeForm(UserChangeForm):
    """Custom form based on the Django Admin form."""

    # This crept in with 1.4...  Apparently assumptions are made about
    # how the form will be used.
    def clean_password(self):
        try:
            return super(ChromaUserChangeForm, self).clean_password()
        except KeyError:
            return ""

    class Meta(UserChangeForm.Meta):
        fields = ("username", "first_name", "last_name", "email")


class UserAuthorization(PatchedDjangoAuthorization):
    def read_list(self, object_list, bundle):
        request = bundle.request
        if request.method is None:
            # IFF the request method is None, then this must be an
            # internal request being done by Resource.get_via_uri()
            # and is therefore safe.
            return object_list
        elif not request.user.is_authenticated():
            # Anonymous sees nothing
            return object_list.none()
        elif request.user.has_perm("add_user"):
            # People who can create users can see all users
            return object_list
        else:
            return object_list.filter(id=request.user.id)


class UserValidation(Validation):
    """A custom Validation class, calling into django.contrib.auth's Form
    classes (can't use FormValidation because we have different forms
    for PUT than for POST)"""

    def is_valid(self, bundle, request=None):
        data = bundle.data or {}
        if request.method in ["PUT", "PATCH"]:
            errors = {}
            try:
                user = get_object_or_404(User, pk=data["id"])
            except KeyError:
                errors["id"] = ["id attribute is mandatory"]
            else:
                change_pw_fields = ["new_password1", "new_password2"]
                if any((True for k in change_pw_fields if data.get(k) is not None)):
                    from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm

                    # Non-superusers always require old_password
                    # Superusers require old_password when editing themselves
                    if not request.user.is_superuser or request.user.id == user.id:
                        form = PasswordChangeForm(user, data)
                    else:
                        form = SetPasswordForm(user, data)

                    if not form.is_valid():
                        errors.update(form.errors)

                    return errors

                form = ChromaUserChangeForm(data, instance=user)

                if not form.is_valid():
                    errors.update(form.errors)

            return errors
        elif request.method == "POST":
            form = UserCreationForm(data)

            if form.is_valid():
                return {}
            else:
                return form.errors
        else:
            raise NotImplementedError


from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpForbidden


class UserResource(ChromaModelResource):
    """
    A user account
    """

    groups = fields.ToManyField(
        "chroma_api.group.GroupResource",
        attribute="groups",
        full=True,
        null=True,
        readonly=True,
        help_text="List of groups that this user is a member of.",
    )
    alert_subscriptions = fields.ToManyField(
        "chroma_api.alert.AlertSubscriptionResource",
        attribute="alert_subscriptions",
        null=True,
        full=True,
        help_text="List of alert subscriptions (alerts for which this user"
        "will be sent emails.  See alert_subscription resource"
        "for format",
    )
    full_name = fields.CharField(help_text="Human readable form derived from ``first_name`` and ``last_name``")

    password1 = fields.CharField(help_text="Used when creating a user (request must be made by a superuser)")
    password2 = fields.CharField(help_text="Password confirmation, must match ``password1``")
    new_password1 = fields.CharField(
        help_text="Used for modifying password (request must be " "made by the same user or by a superuser)"
    )
    new_password2 = fields.CharField(help_text="Password confirmation, must match ``new_password1``")

    is_superuser = fields.BooleanField(readonly=True, help_text="Is the user a superuser", attribute="is_superuser")

    def alter_deserialized_detail_data(self, request, data):
        def handle_groups(group):
            if isinstance(group, dict):
                return group["resource_uri"]
            elif isinstance(group, basestring):
                return group
            elif isinstance(group, Bundle):
                return group
            else:
                raise NotImplementedError(group.__class__)

        if "groups" in data:
            data["groups"] = map(handle_groups, data["groups"])

        return data

    def hydrate_groups(self, bundle):
        from chroma_api.group import GroupResource

        # Prevent non-superusers from modifying their groups
        if not bundle.request.user.is_superuser:
            if bundle.data.get("groups") is not None:
                group_ids = []

                for group in bundle.data["groups"]:
                    if isinstance(group, dict):
                        group_ids.append(int(group["id"]))
                    elif isinstance(group, basestring):
                        group_ids.append(int(GroupResource().get_via_uri(group, bundle.request).id))
                    elif isinstance(group, Bundle):
                        group_ids.append(int(group.obj.id))
                    else:
                        raise NotImplementedError(group.__class__)

                user_group_ids = [int(group.pk) for group in bundle.request.user.groups.all()]

                if not set(group_ids) == set(user_group_ids):
                    raise ImmediateHttpResponse(HttpForbidden())

        return bundle

    # This seems wrong. Without it, the hydration goes awry with what
    # comes in via PUT. We aren't managing user alert subscriptions
    # via the User resource, though, so perhaps this is not so bad.
    def hydrate_alert_subscriptions(self, bundle):
        try:
            del bundle.data["alert_subscriptions"][:]
        except KeyError:
            pass

        return bundle

    def _hydrate_password(self, bundle, key):
        try:
            new_password = bundle.data[key]
            if new_password:
                bundle.obj.set_password(new_password)
        except KeyError:
            pass
        return bundle

    def hydrate_password2(self, bundle):
        return self._hydrate_password(bundle, "password2")

    def hydrate_new_password2(self, bundle):
        return self._hydrate_password(bundle, "new_password2")

    def obj_create(self, bundle, **kwargs):
        bundle = super(UserResource, self).obj_create(bundle, **kwargs)
        from django.contrib.auth.models import Group

        superuser_group = Group.objects.get(name="superusers")
        for g in bundle.obj.groups.all():
            if g == superuser_group:
                bundle.obj.is_superuser = True
                bundle.obj.save()

        return bundle

    def dehydrate_full_name(self, bundle):
        return bundle.obj.get_full_name()

    def delete_detail(self, request, **kwargs):
        if int(kwargs["pk"]) == request.user.id:
            return self.create_response(
                request, {"id": ["Cannot delete currently authenticated user"]}, response_class=HttpBadRequest
            )
        else:
            return super(UserResource, self).delete_detail(request, **kwargs)

    class Meta:
        authentication = AnonymousAuthentication()
        authorization = UserAuthorization()
        queryset = User.objects.all()
        validation = UserValidation()
        fields = [
            "first_name",
            "full_name",
            "groups",
            "id",
            "last_name",
            "new_password1",
            "new_password2",
            "password1",
            "password2",
            "resource_uri",
            "username",
            "email",
        ]
        ordering = ["username", "email"]
        list_allowed_methods = ["get", "post"]
        detail_allowed_methods = ["get", "put", "patch", "delete"]
        always_return_data = True
