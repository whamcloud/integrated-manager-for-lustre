
from django.contrib.auth.models import User

from chroma_api.authentication import AnonymousAuthentication
from tastypie.authorization import DjangoAuthorization
from tastypie.resources import ModelResource
from tastypie import fields


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


class UserResource(ModelResource):
    groups = fields.ToManyField('chroma_api.group.GroupResource', attribute = 'groups', full = True)

    class Meta:
        authentication = AnonymousAuthentication()
        authorization = UserAuthorization()
        queryset = User.objects.all()
