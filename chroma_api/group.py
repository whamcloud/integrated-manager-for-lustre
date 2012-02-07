
from django.contrib.auth.models import Group

from chroma_api.authentication import AnonymousAuthentication
from tastypie.authorization import DjangoAuthorization
from tastypie.resources import ModelResource


class GroupResource(ModelResource):
    class Meta:
        authentication = AnonymousAuthentication()
        authorization = DjangoAuthorization()
        queryset = Group.objects.all()
        filtering = {'name': ['exact', 'iexact']}
