
from django.contrib.auth.models import User

from chroma_api.authentication import AnonymousAuthentication
from tastypie.authorization import DjangoAuthorization
from tastypie.resources import ModelResource
from tastypie import fields

from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from tastypie.validation import Validation
from tastypie.http import HttpBadRequest


class UserAuthorization(DjangoAuthorization):
    def apply_limits(self, request, object_list):
        if not request.user.is_authenticated():
            # Anonymous sees nothing
            return object_list.none()
        elif request.user.has_perm('add_user'):
            # People who can create users can see all users
            return object_list
        else:
            return object_list.filter(id = request.user.id)


class UserValidation(Validation):
    """A custom Validation class, calling into django.contrib.auth's Form
    classes (can't use FormValidation because we have different forms
    for PUT than for POST)"""
    def __init__(self, **kwargs):
        self.post_form = UserCreationForm
        self.put_form = SetPasswordForm
        super(UserValidation, self).__init__(**kwargs)

    def is_valid(self, bundle, request = None):
        data = bundle.data or {}
        print "bundle.data = %s" % bundle.data
        print "data = %s" % bundle.data
        if request.method == "PUT":
            errors = {}
            if not data['password1']:
                errors['password1'] = ['Password may not be blank']
            if not data['password2']:
                errors['password2'] = ['Password may not be blank']

            if data['password1'] and data['password2']:
                if data['password1'] != data['password2']:
                    err = ['Passwords do not match']
                    if 'password2' in errors:
                        errors['password2'].extend(err)
                    else:
                        errors['password2'] = err
            return errors
        elif request.method == "POST":
            form = self.post_form(data)

            if form.is_valid():
                return {}
            else:
                return form.errors
        else:
            raise NotImplementedError

from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpForbidden


class UserResource(ModelResource):
    """
    A user account
    """
    groups = fields.ToManyField('chroma_api.group.GroupResource', attribute = 'groups',
        full = True, null = True, help_text = "List of groups that this user is a member \
                of.  May only be modified by superusers")
    full_name = fields.CharField(help_text = "Human readable form derived from ``first_name`` and ``last_name``")

    password1 = fields.CharField(help_text = "Used for modifying password (request must be\
            made by the same user or by a superuser")
    password2 = fields.CharField(help_text = "Password confirmation, must match ``password1``")

    def hydrate_groups(self, bundle):
        # Prevent non-superusers from modifying their groups
        if not bundle.request.user.is_superuser:
            group_ids = [int(group['pk']) for group in bundle.data['groups']]
            user_group_ids = [group.pk for group in bundle.request.user.groups.all()]
            if not set(group_ids) == set(user_group_ids):
                raise ImmediateHttpResponse(HttpForbidden())
        return bundle

    def hydrate_password1(self, bundle):
        bundle.obj.set_password(bundle.data['password1'])
        return bundle

    def obj_create(self, bundle, request = None, **kwargs):
        bundle = super(UserResource, self).obj_create(bundle, request, **kwargs)
        from django.contrib.auth.models import Group
        superuser_group = Group.objects.get(name = 'superusers')
        for g in bundle.obj.groups.all():
            if g == superuser_group:
                bundle.obj.is_superuser = True
                bundle.obj.save()

        return bundle

    def dehydrate_full_name(self, bundle):
        return bundle.obj.get_full_name()

    def delete_detail(self, request, **kwargs):
        if int(kwargs['pk']) == request.user.id:
            return self.create_response(request, {'id': ["Cannot delete currently authenticated user"]}, response_class = HttpBadRequest)
        else:
            return super(UserResource, self).delete_detail(request, **kwargs)

    class Meta:
        authentication = AnonymousAuthentication()
        authorization = UserAuthorization()
        queryset = User.objects.all()
        validation = UserValidation()
        fields = ['date_joined', 'first_name', 'full_name', 'groups', 'id', 'last_login', 'last_name', 'password1', 'password2', 'resource_uri', 'username', 'email']
        ordering = ['username', 'email']
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'put', 'delete']
