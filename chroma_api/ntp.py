# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_core.models import NTPConfiguration
from chroma_api.utils import StatefulModelResource


class NtpConfigurationResource(StatefulModelResource):
    class Meta:
        queryset = NTPConfiguration.objects.all()
        resource_name = "ntp_configuration"
        list_allowed_methods = ["get", "put"]
        detail_allowed_methods = ["get", "put"]
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
