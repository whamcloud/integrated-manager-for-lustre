# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_api.authentication import AnonymousAuthentication
from chroma_api.host import HostResource
from chroma_core.models import ManagedHost
from chroma_core.models.package import PackageVersion
from django.db.models import Q
from tastypie.authorization import DjangoAuthorization
from tastypie.fields import CharField, ToManyField

from chroma_api.chroma_model_resource import ChromaModelResource


# This class represents a REST style view of the underlying package
# schema which is normalized into PackageInstallation,
# PackageVersion and Package models.

class PackageResource(ChromaModelResource):
    """
    Represents a particular version of a package.  Includes which servers have this package
    installed, and on which servers this package is available.  Filter by ``host`` to
    obtain a report including only packages which are installed on or available to
    a particular host.
    """
    class Meta:
        queryset = PackageVersion.objects.select_related('packageinstallation').select_related('packageavailability').select_related('package')
        resource_name = 'package'
        fields = ['name', 'epoch', 'version', 'release', 'arch', 'installed_hosts', 'available_hosts']
        authentication = AnonymousAuthentication()
        authorization = DjangoAuthorization()
        ordering = ['name']
        list_allowed_methods = ['get']
        detail_allowed_methods = []
        filtering = {'host': ['exact']}

    name = CharField(help_text="Name of the package, for example \"lustre\"")
    # epoch = IntegerField()
    # version = CharField()
    # release = CharField()
    # arch = CharField()

    installed_hosts = ToManyField(HostResource,
                                  attribute=lambda bundle: ManagedHost.objects.filter(
                                      packageinstallation__package_version=bundle.obj), null=True,
                                  help_text="List of URIs of servers on which this package is installed")
    available_hosts = ToManyField(HostResource,
                                  attribute=lambda bundle: ManagedHost.objects.filter(
                                      packageavailability__package_version=bundle.obj), null=True,
                                  help_text="List of URIs of servers on which this package is available")

    def apply_filters(self, request, applicable_filters):
        if 'host' in request.GET:
            host = ManagedHost.objects.get(pk=request.GET['host'])
            return PackageVersion.objects.filter(Q(packageinstallation__host=host) | Q(packageavailability__host=host))
        else:
            return PackageVersion.objects.all()

    def dehydrate_name(self, bundle):
        return bundle.obj.package.name

    def dehydrate_epoch(self, bundle):
        return bundle.obj.epoch

    def dehydrate_arch(self, bundle):
        return bundle.obj.arch

    def dehydrate_version(self, bundle):
        return bundle.obj.version

    def dehydrate_release(self, bundle):
        return bundle.obj.release
