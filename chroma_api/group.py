# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.contrib.auth.models import Group

from chroma_api.authentication import AnonymousAuthentication
from tastypie.authorization import ReadOnlyAuthorization

from chroma_api.chroma_model_resource import ChromaModelResource


class GroupResource(ChromaModelResource):
    """
    A user group.  Users inherit the permissions
    of groups of which they are a member.

    Groups are used internally to refer
    to factory-configured profiles, so this resource
    is read-only.
    """

    class Meta:
        authentication = AnonymousAuthentication()
        authorization = ReadOnlyAuthorization()
        queryset = Group.objects.all()
        filtering = {"name": ["exact", "iexact"]}
        ordering = ["name"]

        list_allowed_methods = ["get"]
        detail_allowed_methods = ["get"]
