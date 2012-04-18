#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.contrib.auth.models import Group

from chroma_api.authentication import AnonymousAuthentication
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.resources import ModelResource


class GroupResource(ModelResource):
    """
    A user group.  Users inherit the permissions
    of groups of which they are a member.

    Chroma groups are used internally to refer
    to factory-configured profiles, so this resource
    is read-only.
    """
    class Meta:
        authentication = AnonymousAuthentication()
        authorization = ReadOnlyAuthorization()
        queryset = Group.objects.all()
        filtering = {'name': ['exact', 'iexact']}

        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
